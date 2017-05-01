#! python3
###############################################################################
# Copyright (c) 2016, PulseRain Technology LLC 
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
###############################################################################




import sys
import signal
import traceback
import msvcrt
import math

from OCD_8051 import OCD_8051
from ROM_Hex_Format import *
from OCD_Input import OCD_Input
from time import sleep

#############################################################################
# Debug Console for the M10 board (with Onchip Debugger on an FP51 core)
#############################################################################

class M10_Console:
    
#############################################################################
# command procedures
#############################################################################
    
    _DEBUG_COUNTER_INDEX_RESET = 1
    _DEBUG_COUNTER_INDEX_SET   = 2
    _TIME_COUNTER_INDEX_RESET  = 3
    _TIME_COUNTER_INDEX_SET    = 4  

    #========================================================================
    #  _string_to_data
    #========================================================================
    def _string_to_data (self, data_string):
        if (data_string.startswith('0x')):
            data = int(data_string[2:], 16)
        else:
            data = int(data_string)
        
        return data
   
    #========================================================================
    #  _do_reset_cpu
    #========================================================================
    def _do_reset_cpu (self):
        self._ocd._serial.reset_output_buffer() 
        self._ocd._serial.reset_input_buffer()        
        
        self._ocd.cpu_reset()
        
        self._ocd._serial.reset_output_buffer() 
        self._ocd._serial.reset_input_buffer()        

    #========================================================================
    #  _do_pause_cpu
    #========================================================================
    def _do_pause_cpu (self):
        self._ocd.cpu_pause (1)

    #========================================================================
    #  _do_resume_cpu
    #========================================================================
    def _do_resume_cpu (self):
        self._ocd.cpu_pause (0)

    #========================================================================
    #  _do_read_cpu_status
    #========================================================================
    def _do_read_cpu_status (self):
        self._ocd.read_cpu_status ()
        
        print ("===> PC:", hex(self._ocd.PC))
        print ("===> debug_stall_flag:", self._ocd.debug_stall_flag)
        print ("===> debug_counter:", self._ocd.debug_counter)
        print ("===> timer_counter:", self._ocd.timer_counter)
        
        if (self._ocd.debug_stall_flag):
            indirect1_direct0 = 0
            addr = OCD_8051.ADDR_MAP['ACC']
            ret_data_byte = self._ocd.data_mem_read_byte (addr, indirect1_direct0)
            print ("===> A: 0x%02x" % ret_data_byte)
    
            addr = OCD_8051.ADDR_MAP['B']
            ret_data_byte = self._ocd.data_mem_read_byte (addr, indirect1_direct0)
            print ("===> B: 0x%02x" % ret_data_byte)
    
            addr = 0
            ret_data_byte = self._ocd.data_mem_read_byte (addr, indirect1_direct0)
            print ("===> R0 (bank0): 0x%02x" % ret_data_byte)
    
            addr = 1
            ret_data_byte = self._ocd.data_mem_read_byte (addr, indirect1_direct0)
            print ("===> R1 (bank0): 0x%02x" % ret_data_byte)
    
            addr = OCD_8051.ADDR_MAP['PSW']
            ret_data_byte = self._ocd.data_mem_read_byte (addr, indirect1_direct0)
            print ("===> PSW: 0x%02x" % ret_data_byte)
            print ("       P: %d" % (ret_data_byte & 1))
            print ("      OV: %d" % ((ret_data_byte >> 2) & 1))
            print ("Reg Bank: %d" % ((ret_data_byte >> 3) & 3))
            print ("      AC: %d" % ((ret_data_byte >> 6) & 1))
            print ("      CY: %d" % ((ret_data_byte >> 7) & 1))
            
            
    #========================================================================
    #  _write_code
    #========================================================================
    def _write_code (self, addr, data):
        offset = 0
        length = len (data)
        addr_end = addr + length
        
        if (addr % 4):
            for i in range (min([(4 - (addr % 4)), length])):
                self._ocd.code_mem_write_byte (addr + offset, data[i])
                offset = offset + 1
        
        total_words = (addr_end - addr - offset) // 4
        total_128byte_frame = total_words //32
        
        for i in range (total_128byte_frame):
            self._ocd.code_mem_write_128byte (addr + offset, data[offset : offset + 128])
            offset = offset + 128
            
        
        for i in range (total_words - total_128byte_frame * 32):
            data_int = (data[offset] << 24) + \
                       (data[offset + 1] << 16) + \
                       (data[offset + 2] << 8) + \
                       (data[offset + 3])
            
            ##print ("write32bit addr = ", addr + offset, "data_int=", hex(data_int))            
            self._ocd.code_mem_write_32bit(addr + offset, data_int)
            offset = offset + 4
        
        for i in range (length - offset):
            self._ocd.code_mem_write_byte (addr + offset, data [offset])
            offset = offset + 1

    #========================================================================
    #  _read_code
    #========================================================================
    def _read_code (self, addr, length):
        offset = 0
        addr_end = addr + length
               
        ret_data = []
        if (addr % 4):
            for i in range (min([(4 - (addr % 4)), length])):
                ret_data = ret_data + [self._ocd.code_mem_read_byte (addr + offset)]
                ##print ("byte addr = ", addr + offset, "ret data = ", ret_data)
                offset = offset + 1
            
        total_words = (addr_end - addr - offset) // 4
        
        for i in range (total_words):
            tmp = self._ocd.code_mem_read_32bit(addr + offset)
            ##print ("addr = ", addr + offset, "tmp = ", tmp)
            ##tmp_reversed = tmp[::-1]
            ret_data = ret_data + tmp
            offset = offset + 4
        
        for i in range (length - offset):
            ret_data = ret_data + [self._ocd.code_mem_read_byte (addr + offset)]
            offset = offset + 1
    
        return ret_data
        
    #========================================================================
    #  _do_write_code
    #========================================================================
    def _do_write_code (self):
        addr = self._args[1]
        
        data = []
        for i in range (len (self._args) - 2):
            data = data + [self._args[i + 2]]
        
        print ("==> addr:", addr)
        print ("==> data:", data)
        self._write_code (self._string_to_data(addr), [self._string_to_data(i) for i in data])        

    #========================================================================
    #  _do_read_code
    #========================================================================
    def _do_read_code (self):
        self._ocd.read_cpu_status ()
        
        if (self._ocd.debug_stall_flag == 0):
            print ("==> Can't read code because CPU is still running")
            return        
    
        addr = self._args[1]
        length = self._args[2]
        
        ret_data = self._read_code (self._string_to_data(addr), self._string_to_data(length))
        
        if (len(self._args) > 3):
            f = open(self._args[3], 'w')
            for item in ret_data:
                f.write('%d\n' % (item))
                
        print ("==> addr:", addr)
        print ("==> data:", [hex(i) for i in ret_data])

    #========================================================================
    #  _do_load_hex_file
    #========================================================================
    def _do_load_hex_file (self):
        intel_hex_file =  Intel_Hex(self._args[1])
        
        if (len (intel_hex_file.data_record_list) == 0):
            return
            
        if (len(self._args) > 2):
            try:
                f = open(self._args[2], 'w')
            except IOError:
                print ("Fail to open: ", self._args[2])
                return
                
        self._do_pause_cpu()
        print ("CPU paused");
        print ("CPU reset ...")
        self._do_reset_cpu()        
        sleep(0.5)
        print ("Loading...", self._args[1])
        
        last_addr = intel_hex_file.data_record_list[-2].address + len(intel_hex_file.data_record_list[-1].data_list)
        len_completed = 0
        
        address = 0
        merge_data_list = []
        
        
        for record in intel_hex_file.data_record_list:
            #print ("xxxxaddr=", record.address, "data=", record.data_list)
            if (len(merge_data_list) == 0):
                address = record.address
                merge_data_list = record.data_list
                #print ("YY addr = ", address, " ", len (merge_data_list))
            elif ((address + len (merge_data_list)) == record.address):
                merge_data_list = merge_data_list + record.data_list
                
                #print ("WW addr = ", address, " ", len (merge_data_list))
                #print (merge_data_list)
                
                
            else:
                #print ("XXXXXXXXXXXXXXX ", address, " ", len(merge_data_list))
                self._write_code (address, merge_data_list)
                #print ("YYYYYYYYYYYYYYYY")
                
                len_completed = len_completed + len(merge_data_list)
                
                load_progress = math.ceil(len_completed * 100 / last_addr);
                if (load_progress > 100):
                    load_progress = 100
                
                print ("\b\b\b\b\b\b\b\b\b\b\b\b\b\b\b\b\b\b\b\b\b\b\b\b\b\b\b\b\b\b\b\b\b\b\b\b\b\b\b\b\b\b", end="")            
                print ("%d%% completed" % load_progress, end="")
                sys.stdout.flush()    
                
                if (len(self._args) > 2):
                    f.write('addr %d\n' % (address))
                    
                    for item in merge_data_list:
                        f.write('%d\n' % (item))
                        
                address = record.address
                merge_data_list = record.data_list



                
        if (len(self._args) > 2):
            f.close()
                
        self._do_resume_cpu()
        print ("\nCPU reset ...")
        self._do_reset_cpu()        
        print ("Done: ", last_addr, " Byte(s)")
        print ("CPU is runnning")

    #========================================================================
    #  _do_counter_set
    #========================================================================
    def _do_counter_set (self):
        print ("Configure debug counter and timer counter")
        
        config = self._string_to_data(self._args[1])
        
        debug_counter_reset  = (config >> M10_Console._DEBUG_COUNTER_INDEX_RESET) & 1
        debug_counter_enable = (config >> M10_Console._DEBUG_COUNTER_INDEX_SET) & 1
        timer_counter_reset  = (config >> M10_Console._TIME_COUNTER_INDEX_RESET) & 1
        timer_counter_enable = (config >> M10_Console._TIME_COUNTER_INDEX_SET) & 1
        
        print ("timer_counter_reset = ", timer_counter_reset)
        print ("debug_counter_enable = ", debug_counter_enable)
        print ("timer_counter_reset = ", timer_counter_reset)
        print ("timer_counter_enable = ", timer_counter_enable)
        
        self._ocd.counter_config (debug_counter_reset, debug_counter_enable, timer_counter_reset, timer_counter_enable)
                
    #========================================================================
    #  _do_break_point_on
    #========================================================================
    def _do_break_point_on (self):
        print ("Set breakpoint on address", self._args[1], "and", self._args[2])
        
        self._ocd.set_breakpoint (self._string_to_data (self._args[1]), self._string_to_data (self._args[2])) 

    #========================================================================
    #  _do_break_point_off
    #========================================================================
    def _do_break_point_off (self):
        print ("Set breakpoint off")
        
        self._ocd.breakpoint_off ()
        
    #========================================================================
    #  _do_continue
    #========================================================================
    def _do_continue (self):
        print ("run continue")
        
        self._ocd.run_pulse ()
        self._do_read_cpu_status()
        
        if (self._ocd.debug_stall_flag):
            ret_data = self._read_code (self._ocd.PC, 8)
            self._disassemble (self._ocd.PC, ret_data)
        
        print ("\n")

    #========================================================================
    #  _do_read_data
    #========================================================================
    def _do_read_data (self):
        
        self._ocd.read_cpu_status ()
        
        if (self._ocd.debug_stall_flag == 0):
            print ("==> Can't read data because CPU is still running")
            return        
        
        if (self._args[1].upper() in OCD_8051.ADDR_MAP):
            addr = OCD_8051.ADDR_MAP [self._args[1].upper()]
        else:
            addr = self._string_to_data(self._args[1])
           
        if (len(self._args) > 2):
            length = self._args[2]
        else:
            length = 1
            
        if (len(self._args) > 3):
            indirect1_direct0 = self._string_to_data(self._args[3])
        else:
            indirect1_direct0 = 0
        
        
        ret_data = []
            
        for i in range (length):
            ret_data_byte = self._ocd.data_mem_read_byte (addr, indirect1_direct0)
            ret_data.append (ret_data_byte)
        
        if (len(self._args) > 4):
            f = open(self._args[4], 'w')
            for item in ret_data:
                f.write('%d\n' % (item))
                
        print ("==> addr:", addr)
        print ("==> data:", [hex(i) for i in ret_data])

    #========================================================================
    #  _do_write_data
    #========================================================================
    def _do_write_data (self):
        self._ocd.read_cpu_status ()
        
        if (self._ocd.debug_stall_flag == 0):
            print ("==> Can't write data because CPU is still running")
            return        
         
        
        if (self._args[1].upper() in OCD_8051.ADDR_MAP):
            addr = OCD_8051.ADDR_MAP [self._args[1].upper()]
        else:
            addr = self._string_to_data(self._args[1])
        
        indirect1_direct0 = self._indirect1_direct0
        
        data = []
        for i in range (len (self._args) - 2):
            data_byte = self._string_to_data(self._args[i + 2])
            self._ocd.data_mem_write_byte (addr, data_byte, indirect1_direct0)
            data = data + [data_byte]
      
      
        print ("==> addr:", addr)
        print ("==> data:", data)
                
    #========================================================================
    #  _do_write_data_direct
    #========================================================================
    def _do_write_data_direct (self):
        self._indirect1_direct0 = 0;
        self._do_write_data()

    #========================================================================
    #  _do_write_data_indirect
    #========================================================================
    def _do_write_data_indirect (self):
        self._indirect1_direct0 = 1;
        self._do_write_data()
        
    #========================================================================
    #  _disassemble
    #========================================================================
    def _disassemble (self, start_addr, code_list):
        offset = 0
        
        while (offset < len (code_list)):
            op_code = code_list [offset]
            
            (cmd, cmd_size, cmd_nature) = OCD_8051.INSTRUCTIONS[op_code]
            
            if ((offset + cmd_size) < len (code_list)):
                print ("{0:04X}\t".format (start_addr + offset), end="")
                
                for i in range (cmd_size):
                    print ("%02X " % code_list [offset + i], end="")
                    
                if (cmd_size < 3):
                    for i in range (3 - cmd_size):
                        print ("   ", end="")
                
                print ("\t:   ", end="")
                
                print (cmd, end="")
                for i in range (6 - len(cmd)):
                    print (" ", end="")
                        
                if (cmd_size == 1):
                    print (cmd_nature)
                else:
                    i = 0
                    j = 0
                    cmd_nature_list = cmd_nature.split()
                    for op in cmd_nature_list:
                        i = i + 1
                        if (len(op)):
                            if ( (ord(op[0]) >= ord('a')) and (ord(op[0]) <= ord('z')) ):
                                j = j + 1
                                if (ord(op[0]) == ord('i')):
                                    print ("#", end="")
                                
                                if (op.endswith("/")):
                                    print ("/", end="")
                                
                                if (op.endswith("16")):
                                    print ("0x{0:02X}{1:02X}".format(code_list[offset + j], code_list[offset + j + 1]), end="")
                                    j = j + 1
                                else:
                                    if ((ord(op[0]) == ord('d')) and (code_list[offset + j] in list(OCD_8051.ADDR_MAP.values()))):
                                        print (list(OCD_8051.ADDR_MAP.keys())[list(OCD_8051.ADDR_MAP.values()).index(code_list[offset + j])], end="")
                                    elif ((ord(op[0]) == ord('b')) and (code_list[offset + j] in list(OCD_8051.BIT_MAP.values()))):
                                        print (list(OCD_8051.BIT_MAP.keys())[list(OCD_8051.BIT_MAP.values()).index(code_list[offset + j])], end="")
                                    else:    
                                        print ("0x{0:02X}".format(code_list[offset + j]), end="")
                                    
                                    
                            else:
                                print (op, end="")
                                
                        if (i < len (cmd_nature_list)):
                            print (", ", end="")
                            
                    print (" ")
                    
                    
            offset = offset + cmd_size
                
    #========================================================================
    #  _do_disassemble
    #========================================================================
    def _do_disassemble (self):
        self._ocd.read_cpu_status ()
        
        if (self._ocd.debug_stall_flag == 0):
            print ("==> Can't read code because CPU is still running")
            return        
        
    
        addr = self._string_to_data(self._args[1])
        length = self._string_to_data(self._args[2])
        
        ret_data = self._read_code (addr, length)
        
        self._disassemble (addr, ret_data)
        
        print ("\n")
        #print (ret_data)
    
    #========================================================================
    #  _do_uart_select
    #========================================================================
    def _do_uart_select (self):
        self._ocd.uart_select (1 - self._stdin.uart_raw_mode_enable)

    #========================================================================
    #  _do_uart_switch
    #========================================================================
    def _do_uart_switch (self):
        self._stdin.uart_raw_mode_enable = 1 - self._stdin.uart_raw_mode_enable
        self._ocd._serial.reset_output_buffer()    
        self._ocd._serial.reset_input_buffer()
        self._do_uart_select()
        print ("\n================================================================================")
        self._ocd._serial.reset_output_buffer() 
        self._ocd._serial.reset_input_buffer() 
        if (self._stdin.uart_raw_mode_enable):
            print ("UART Raw Mode")
        else:
            print ("Debug Console Mode")
        print ("================================================================================")
        
        self._ocd._serial.write ([ord('\r')])
        sleep(0.5)
        if (self._ocd._serial.in_waiting):
            r = self._ocd._serial.read (self._ocd._serial.in_waiting)  
            prt_out = ""
            for i in r:
                if (i < 128):
                    prt_out = prt_out + chr(i) 
            #print (prt_out, end="")
            #sys.stdout.flush()    

    #========================================================================
    #  _do_load_hex_and_switch
    #========================================================================
    def _do_load_hex_and_switch (self):
        self._do_load_hex_file()
        self._do_uart_switch()
        
#############################################################################
# static variables
#############################################################################
    
    _OCD_CONSOLE_PROMPT = "\n>> "
    
    def _do_help (self):
         if (len(self._args) > 1):
            if (self._args[1] in M10_Console._OCD_CONSOLE_CMD):
                print ("Usage:\n      ", self._args[1], OCD_Console._OCD_CONSOLE_CMD[self._args[1]][1])
                print ("Description:\n      ", OCD_Console._OCD_CONSOLE_CMD[self._args[1]][2])
                
            else:
                print ("Unknow command")        
         else:
            print ("available commands:")
            for key, value in M10_Console._OCD_CONSOLE_CMD.items():
                print (" ", key)
   

    #========================================================================
    # _dummy_exit
    #------------------------------------------------------------------------
    # Remarks:
    #    This function never gets called. But need this as a place holder 
    # for tools that can convert python script into .exe files.
    #========================================================================
    def _dummy_exit (self):
        None

   
    _OCD_CONSOLE_CMD = {
        'help'                 : (_do_help,              "", "list command info"), 
        'reset'                : (_do_reset_cpu,         "", "reset cpu"),
        'pause'                : (_do_pause_cpu,         "", "pause cpu"),
        'resume'               : (_do_resume_cpu,        "", "resume running"),
        'status'               : (_do_read_cpu_status,   "", "read cpu status"),
        'load_hex'             : (_do_load_hex_file,     "file_name", "load hex file into code memory"),
        'load_hex_and_switch'  : (_do_load_hex_and_switch, "file_name", "load hex file into code memory, and switch uart to raw mode"),
        'write_code'           : (_do_write_code,        "addr code_list", "write code memory"),
        'read_code'            : (_do_read_code,         "addr length", "read code memory"),
        'counter_config'       : (_do_counter_set,        "configuration", "config debug counter and timer counter. \
                                                            \n\t bit 0: Reserved;                     \
                                                            \n\t bit 1: DEBUG_COUNTER_INDEX_RESET;    \
                                                            \n\t bit 2: DEBUG_COUNTER_INDEX_SET;      \
                                                            \n\t bit 3: TIME_COUNTER_INDEX_RESET;     \
                                                            \n\t bit 4: TIME_COUNTER_INDEX_SET;"), 
        'break_on'             : (_do_break_point_on,     "break_point_addr1 break_point_addr2", "turn on break point"),
        'break_off'            : (_do_break_point_off,    "", "turn off break point"),
        'next'                 : (_do_continue,           "", "continue to run"),
        'read_data'            : (_do_read_data,          "addr length", "read data memory"),
        'write_direct_data'    : (_do_write_data_direct,  "addr data_list", "write directly mapped data memory"),
        'write_indirect_data'  : (_do_write_data_indirect,"addr data_list", "write indirectly mapped data memory"),
        'disassemble'          : (_do_disassemble,        "addr length",    "dis-assemble code memory"),
        'uart_switch'          : (_do_uart_switch,        "uart_switch",    "toggle uart between OCD and CPU core"),
        'exit'                 : (_dummy_exit,            " ", "exit console")
    }
    
 
   
       
#############################################################################
# Methods
#############################################################################

    #========================================================================
    #  __init__
    #========================================================================
    def __init__ (self, ocd):
        self._ocd = ocd
        if (ocd._serial.in_waiting):
            r = ocd._serial.read (ocd._serial.in_waiting) # clear the uart receive buffer 
        
        print (" Hint: Please use ctrl-d to switch between UART Raw Mode and Debug Console Mode")          
        self._stdin = OCD_Input(">> ", M10_Console._OCD_CONSOLE_CMD.keys())
        self._stdin.uart_raw_mode_enable = 0
        self._do_uart_select()

    #========================================================================
    #  _execute_cmd
    #========================================================================
    def _execute_cmd (self):
        #try:
            M10_Console._OCD_CONSOLE_CMD[self._args[0]][0](self)
        #except Exception:
         #   print ("Exception when executing", self._args[0])
            

    #========================================================================
    #  _line_handle
    #========================================================================
    def _line_handle (self, line):
        
        #try:
        self._args = line.split()
        
        if (len(self._args) == 0):
            print ("empty line!");
        elif (self._args[0] not in M10_Console._OCD_CONSOLE_CMD):
            print ("unknown command ", self._args[0]);
        else:
            #print ("Execute command: ", line.strip());
            self._execute_cmd ()
        #except Exception:
         #   print ("eeeeeeeeeeeeeeeeeeee\n", end="");
        
        
    #########################################################################
    # This is the main loop    
    #########################################################################
    def run (self):
        while(1):
            try:
                line = self._stdin.input()
                if (line == "exit"):
                    print ("\nGoodbye!!!")
                    return
            except Exception:
                if (self._stdin.uart_raw_mode_enable == 0):
                    print ("type \"exit\" to end console session \n", end="");

            if (self._stdin.uart_raw_mode_enable):
                
                if (line == "uart_switch"):
                    self._line_handle (line)
                    self._ocd._serial.reset_input_buffer()
                    
                elif (len(line)):
                    print (line, end="")
                    sys.stdout.flush()
                    serial_out = [ord(i) for i in line]
                    self._ocd._serial.write(serial_out)
                
                # read data out from COM port
                if (self._ocd._serial.in_waiting):
                    r = self._ocd._serial.read (self._ocd._serial.in_waiting)  
                    
                    prt_out = ""
                    for i in r:
                        if (i < 128):
                            prt_out = prt_out + chr(i) 
                    print (prt_out, end="")
                    sys.stdout.flush()
     
            else:
                self._ocd._serial.reset_input_buffer()
                self._line_handle (line)
            
#==============================================================================
# main            
#==============================================================================
            
def main():

    com_port = "COM4"
    if (len(sys.argv) > 1):
        com_port = sys.argv[1]
    
    try:
        ocd = OCD_8051 (com_port, 115200, verbose=0)
    except:
        print ("Failed to open COM port")
        sys.exit(1)
        
    console = M10_Console(ocd)
    console.run()
    
    
if __name__ == "__main__":
    main()
