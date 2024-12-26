
from . import probe, probe_eddy_current, manual_probe
import math
import configparser

class ZoffsetCalibration:
    def __init__(self, config):
        self.printer = config.get_printer()
        self.config = config
        x_pos_center, y_pos_center = config.getfloatlist("center_xy_position", count=2)
        x_pos_endstop, y_pos_endstop = config.getfloatlist("endstop_xy_position", count=2)
        self.center_x_pos, self.center_y_pos = x_pos_center, y_pos_center
        self.endstop_x_pos, self.endstop_y_pos = x_pos_endstop, y_pos_endstop
        self.z_hop = config.getfloat("z_hop", default=10.0)
        self.z_hop_speed = config.getfloat('z_hop_speed', 5., above=0.)
        self.zconfig = config.getsection('stepper_z')
        self.endstop_pin = self.zconfig.get('endstop_pin')
        self.speed = config.getfloat('speed', 180.0, above=0.)
        self.internal_endstop_offset = config.getfloat('internal_endstop_offset', default=0.)
        self.gcode = self.printer.lookup_object('gcode')
        self.gcode_move = self.printer.lookup_object('gcode_move')
        self.gcode.register_command("Z_OFFSET_CALIBRATION", self.cmd_Z_OFFSET_CALIBRATION, desc=self.cmd_Z_OFFSET_CALIBRATION_help)
        self.last_toolhead_pos = self.last_kinematics_pos = None
        
        pprobe = self.printer.lookup_object("probe")
        self.x_offset, self.y_offset, self.z_offset = pprobe.get_offsets()
        if self.x_offset == 0 and self.y_offset == 0:
            raise config.error("ZoffsetCalibration: Check the x and y offset from [probe] - it seems both are 0 and the Probe can't be at the same position as the nozzle :-)")
        
        probe_pressure = config.getsection('probe_pressure')
        self.x_offsetp = probe_pressure.getfloat('x_offset', note_valid=False)
        self.y_offsetp = probe_pressure.getfloat('y_offset', note_valid=False)
    
    def _call_macro(self, macro):
        self.gcode.run_script_from_command(macro)

    def cmd_Z_OFFSET_CALIBRATION(self, gcmd):
        ## get eddy object
        objs_list = self.printer.lookup_objects('probe_eddy_current')
        name, pprobe_eddy = objs_list[0]
        
        if pprobe_eddy.calibration.is_calibrated() == True and gcmd.get("METHOD", "default") == 'default':
            gcmd.respond_info("ZoffsetCalibration: Eddy data already exists")
            return
        
        if 'homing_override' in self.printer.objects:
            phoming = self.printer.lookup_object('homing_override')
        else:
            phoming = self.printer.lookup_object('homing')
        self.toolhead = self.printer.lookup_object('toolhead')
        pheater_bed = self.printer.lookup_object('heater_bed')
        pheater_extruder = self.printer.lookup_object('extruder')
        z_max_position = self.zconfig.getfloat('position_max')
        bed_temp = gcmd.get_float('BED_TEMP', default=65.0)
        extruder_temp = gcmd.get_float('EXTRUDER_TEMP', default=130.0)

        gcmd_set_bed_temp = self.gcode.create_gcode_command("M140", "M140", {'S': bed_temp})
        gcmd_set_extruder_temp = self.gcode.create_gcode_command("M104", "M104", {'S': extruder_temp})
        pheater_bed.cmd_M140(gcmd_set_bed_temp)
        pheater_extruder.cmd_M104(gcmd_set_extruder_temp)
        gcmd_wait_bed_temp = self.gcode.create_gcode_command("M109", "M190", {'S': bed_temp})
        gcmd_wait_extruder_temp = self.gcode.create_gcode_command("M109", "M109", {'S': extruder_temp})
        pheater_bed.cmd_M190(gcmd_wait_bed_temp)
        pheater_extruder.cmd_M109(gcmd_wait_extruder_temp)

        ## home xy
        curtime = self.printer.get_reactor().monotonic()
        if 'xy' not in self.toolhead.get_status(curtime)['homed_axes']:
            gcmd_G28 = self.gcode.create_gcode_command("G28", "G28", {'X': 0, 'Y': 0})
            phoming.cmd_G28(gcmd_G28)
        
        pos = self.toolhead.get_position()
        pos[2] = z_max_position
        self.toolhead.set_position(pos, homing_axes=(0, 1, 2))

        gcmd_offset = self.gcode.create_gcode_command("SET_GCODE_OFFSET",
                                                      "SET_GCODE_OFFSET",
                                                      {'Z': 0})
        self.gcode_move.cmd_SET_GCODE_OFFSET(gcmd_offset)

        gcmd.respond_info("ZoffsetCalibration: Pressure move ...")
        self.toolhead.manual_move([self.endstop_x_pos, self.endstop_y_pos], self.speed)

        gcmd.respond_info("ZoffsetCalibration: Pressure probing ...")
        self._call_macro("GET_PRESSURE_TARE")
        zendstop_p = self.printer.lookup_object('probe_pressure').run_probe(gcmd)
        
        reprobe_cnt = 1
        while True:
            if(reprobe_cnt >= 6):
                self.gcode.run_script_from_command('M117 Tip code: 109')
                raise gcmd.error('ZoffsetCalibration: Pressure probe more than five times.')
            # Perform Z Hop
            if self.z_hop:
                pos = self.toolhead.get_position()
                pos[2] += 5
                if pos[2] > z_max_position:
                    pos[2] = z_max_position
                self.toolhead.manual_move([None, None, pos[2]], 5)
            gcmd.respond_info("ZoffsetCalibration: Pressure verifying the difference between before and after %d/5." % (reprobe_cnt))
            self._call_macro("GET_PRESSURE_TARE")
            zendstop_p1 = self.printer.lookup_object('probe_pressure').run_probe(gcmd)
            diff_z = abs(zendstop_p1[2] - zendstop_p[2])
            zendstop_p = zendstop_p1
            if diff_z <= 0.03:
                gcmd.respond_info("ZoffsetCalibration: Pressure check success.")
                break
            reprobe_cnt += 1
        
        # Perform Z Hop
        if self.internal_endstop_offset != 0.:
            pos = self.toolhead.get_position()
            self.toolhead.manual_move([None, None, pos[2] - (2 * self.internal_endstop_offset) + 0.1], self.z_hop_speed)
            
        pos = self.toolhead.get_position()
        pos[2] = 0.1
        self.toolhead.set_position(pos, homing_axes=(0, 1, 2))
        
        if pprobe_eddy.calibration.is_calibrated() == True and gcmd.get("METHOD", "default") == 'default':
            gcmd.respond_info("ZoffsetCalibration: Eddy data already exists")
            return
        
        ## calibrate LDC1612 device current
        if pprobe_eddy.sensor_helper.dccal.get_drive_current() is None:
            self.toolhead.manual_move([None, None, 20.], self.z_hop_speed)
            gcmd_LDC = self.gcode.create_gcode_command("cmd_LDC_CALIBRATE", "cmd_LDC_CALIBRATE", {})
            pprobe_eddy.sensor_helper.dccal.cmd_LDC_CALIBRATE(gcmd_LDC)
        else:
            self.toolhead.manual_move([None, None, 5.], self.z_hop_speed)
            
        ## eddy part
        gcmd_EDDY = self.gcode.create_gcode_command("cmd_EDDY_CALIBRATE", "cmd_EDDY_CALIBRATE", {'PROBE_SPEED': 90.})
        gcmd_ACCEPT = self.gcode.create_gcode_command("cmd_ACCEPT", "cmd_ACCEPT", {'Z': 0.})
        
        manual_probe_helper = pprobe_eddy.calibration.cmd_EDDY_CALIBRATE(gcmd_EDDY)
        self.toolhead.manual_move([None, None, self.internal_endstop_offset - 0.1], 5)
        manual_probe_helper.cmd_ACCEPT(gcmd_ACCEPT)
        
    def set_offset(self, offset):
        # reset pssible existing offset to zero
        gcmd_offset = self.gcode.create_gcode_command("SET_GCODE_OFFSET",
                                                      "SET_GCODE_OFFSET",
                                                      {'Z': 0})
        self.gcode_move.cmd_SET_GCODE_OFFSET(gcmd_offset)
        # set new offset
        gcmd_offset = self.gcode.create_gcode_command("SET_GCODE_OFFSET",
                                                      "SET_GCODE_OFFSET",
                                                      {'Z': offset})
        self.gcode_move.cmd_SET_GCODE_OFFSET(gcmd_offset)

    cmd_Z_OFFSET_CALIBRATION_help = "Test endstop and bed surface to calcualte g-code offset for Z"
    
def load_config(config):
    return ZoffsetCalibration(config)
