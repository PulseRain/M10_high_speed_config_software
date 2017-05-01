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
import serial
from ROM_Hex_Format import Intel_Hex
from CRC16_CCITT import CRC16_CCITT

#############################################################################
# Onchip Debugger for FP51 (1T 8051 core from PulseRain Technology, LLC) 
#############################################################################

class OCD_8051:
#############################################################################
# 8051 address map
#############################################################################
    
    ADDR_MAP = {
        'ACC'                  : 0xE0, 
        'A'                    : 0xE0,
        'B'                    : 0xF0,
        'PSW'                  : 0xD0,
        'IP'                   : 0xB8,
        'P3'                   : 0xB0,
        'IE'                   : 0xA8,
        'P2'                   : 0xA0,
        'SBUF'                 : 0x99,
        'SCON'                 : 0x98,
        'P1'                   : 0x90,
        'TH1'                  : 0x8D,
        'TH0'                  : 0x8C,
        'TL1'                  : 0x8B,
        'TL0'                  : 0x8A,
        'TMOD'                 : 0x89,
        'TCON'                 : 0x88,
        'PCON'                 : 0x87,
        'DPH'                  : 0x83,
        'DPL'                  : 0x82,
        'SP'                   : 0x81,
        'P0'                   : 0x80
    }
    
    BIT_MAP = {
        'P0_0'                 : 0x80,
        'P0_1'                 : 0x81,
        'P0_2'                 : 0x82,
        'P0_3'                 : 0x83,
        'P0_4'                 : 0x84,
        'P0_5'                 : 0x85,
        'P0_6'                 : 0x86,
        'P0_7'                 : 0x87,
        
        'IT0'                  : 0x88,
        'IE0'                  : 0x89,
        'IT1'                  : 0x8A,
        'IE1'                  : 0x8B,
        'TR0'                  : 0x8C,
        'TF0'                  : 0x8D,
        'TR1'                  : 0x8E,
        'TF1'                  : 0x8F,
        
        'P1_0'                 : 0x90,
        'P1_1'                 : 0x91,
        'P1_2'                 : 0x92,
        'P1_3'                 : 0x93,
        'P1_4'                 : 0x94,
        'P1_5'                 : 0x95,
        'P1_6'                 : 0x96,
        'P1_7'                 : 0x97,
        
        'RI'                   : 0x98,
        'TI'                   : 0x99,
        'RB8'                  : 0x9A,
        'TB8'                  : 0x9B,
        'REN'                  : 0x9C,
        'SM2'                  : 0x9D,
        'SM1'                  : 0x9E,
        'SM0'                  : 0x9F,
        
        'P2_0'                 : 0xA0,
        'P2_1'                 : 0xA1,
        'P2_2'                 : 0xA2,
        'P2_3'                 : 0xA3,
        'P2_4'                 : 0xA4,
        'P2_5'                 : 0xA5,
        'P2_6'                 : 0xA6,
        'P2_7'                 : 0xA7,
        
        'EX0'                  : 0xA8,
        'ET0'                  : 0xA9,
        'EX1'                  : 0xAA,
        'ET1'                  : 0xAB,
        'ES'                   : 0xAC,
        'EA'                   : 0xAF,
        
        'RXD'                  : 0xB0,
        'TXD'                  : 0xB1,
        'INT0_N'               : 0xB2,
        'INT1_N'               : 0xB3,
        'T0'                   : 0xB4,
        'T1'                   : 0xB5,
        'WR_N'                 : 0xB6,
        'RD_N'                 : 0xB7,
        
        'PX0'                  : 0xB8,
        'PT0'                  : 0xB9,
        'PX1'                  : 0xBA,
        'PT1'                  : 0xBB,
        'PS'                   : 0xBC,
        
        'P'                    : 0xD0,
        'F1'                   : 0xD1,
        'OV'                   : 0xD2,
        'RS0'                  : 0xD3,
        'RS1'                  : 0xD4,
        'F0'                   : 0xD5,
        'AC'                   : 0xD6,
        'CY'                   : 0xD7
    }
    
    INSTRUCTIONS = {
       0x00                :  ("NOP",    1, ""),
       0x01                :  ("AJMP",   2, "code"),
       0x02                :  ("LJMP",   3, "code16"),
       0x03                :  ("RR",     1, "A"),
       0x04                :  ("INC",    1, "A"),
       0x05                :  ("INC",    2, "data"),
       0x06                :  ("INC",    1, "@R0"),
       0x07                :  ("INC",    1, "@R1"),
       0x08                :  ("INC",    1, "R0"),
       0x09                :  ("INC",    1, "R1"),
       0x0A                :  ("INC",    1, "R2"),
       0x0B                :  ("INC",    1, "R3"),
       0x0C                :  ("INC",    1, "R4"),
       0x0D                :  ("INC",    1, "R5"),
       0x0E                :  ("INC",    1, "R6"),
       0x0F                :  ("INC",    1, "R7"),
       0x10                :  ("JBC",    3, "bit code"),
       0x11                :  ("ACALL",  2, "code"),
       0x12                :  ("LCALL",  3, "code16"),
       0x13                :  ("RRC",    1, "A"),
       0x14                :  ("DEC",    1, "A"),
       0x15                :  ("DEC",    2, "data"),
       0x16                :  ("DEC",    1, "@R0"),
       0x17                :  ("DEC",    1, "@R1"),
       0x18                :  ("DEC",    1, "R0"),
       0x19                :  ("DEC",    1, "R1"),
       0x1A                :  ("DEC",    1, "R2"),
       0x1B                :  ("DEC",    1, "R3"),
       0x1C                :  ("DEC",    1, "R4"),
       0x1D                :  ("DEC",    1, "R5"),
       0x1E                :  ("DEC",    1, "R6"),
       0x1F                :  ("DEC",    1, "R7"),
       0x20                :  ("JB",     3, "bit code"),
       0x21                :  ("AJMP",   2, "code"),
       0x22                :  ("RET",    1, ""),
       0x23                :  ("RL",     1, "A"),
       0x24                :  ("ADD",    2, "A immediate"),
       0x25                :  ("ADD",    2, "A data"),
       0x26                :  ("ADD",    1, "A, @R0"),
       0x27                :  ("ADD",    1, "A, @R1"),
       0x28                :  ("ADD",    1, "A, R0"),
       0x29                :  ("ADD",    1, "A, R1"),
       0x2A                :  ("ADD",    1, "A, R2"),
       0x2B                :  ("ADD",    1, "A, R3"),
       0x2C                :  ("ADD",    1, "A, R4"),
       0x2D                :  ("ADD",    1, "A, R5"),
       0x2E                :  ("ADD",    1, "A, R6"),
       0x2F                :  ("ADD",    1, "A, R7"),
       0x30                :  ("JNB",    3, "bit code"),
       0x31                :  ("ACALL",  1, "code"),
       0x32                :  ("RETI",   1, ""),
       0x33                :  ("RLC",    1, "A"),
       0x34                :  ("ADDC",   2, "A immediate"),
       0x35                :  ("ADDC",   2, "A data"),
       0x36                :  ("ADDC",   1, "A, @R0"),
       0x37                :  ("ADDC",   1, "A, @R1"),
       0x38                :  ("ADDC",   1, "A, R0"),
       0x39                :  ("ADDC",   1, "A, R1"),
       0x3A                :  ("ADDC",   1, "A, R2"),
       0x3B                :  ("ADDC",   1, "A, R3"),
       0x3C                :  ("ADDC",   1, "A, R4"),
       0x3D                :  ("ADDC",   1, "A, R5"),
       0x3E                :  ("ADDC",   1, "A, R6"),
       0x3F                :  ("ADDC",   1, "A, R7"),
       0x40                :  ("JC",     2, "code"),
       0x41                :  ("AJMP",   2, "code"),
       0x42                :  ("ORL",    2, "data A"),
       0x43                :  ("ORL",    3, "data immediate"),
       0x44                :  ("ORL",    2, "A immediate"),
       0x45                :  ("ORL",    2, "A data"),
       0x46                :  ("ORL",    1, "A, @R0"),
       0x47                :  ("ORL",    1, "A, @R1"),
       0x48                :  ("ORL",    1, "A, R0"),
       0x49                :  ("ORL",    1, "A, R1"),
       0x4A                :  ("ORL",    1, "A, R2"),
       0x4B                :  ("ORL",    1, "A, R3"),
       0x4C                :  ("ORL",    1, "A, R4"),
       0x4D                :  ("ORL",    1, "A, R5"),
       0x4E                :  ("ORL",    1, "A, R6"),
       0x4F                :  ("ORL",    1, "A, R7"),
       0x50                :  ("JNC",    2, "code"),
       0x51                :  ("ACALL",  2, "code"),
       0x52                :  ("ANL",    2, "data A"),
       0x53                :  ("ANL",    3, "data immediate"),
       0x54                :  ("ANL",    2, "A immediate"),
       0x55                :  ("ANL",    2, "A data"),
       0x56                :  ("ANL",    1, "A, @R0"),
       0x57                :  ("ANL",    1, "A, @R1"),
       0x58                :  ("ANL",    1, "A, R0"),
       0x59                :  ("ANL",    1, "A, R1"),
       0x5A                :  ("ANL",    1, "A, R2"),
       0x5B                :  ("ANL",    1, "A, R3"),
       0x5C                :  ("ANL",    1, "A, R4"),
       0x5D                :  ("ANL",    1, "A, R5"),
       0x5E                :  ("ANL",    1, "A, R6"),
       0x5F                :  ("ANL",    1, "A, R7"),
       0x60                :  ("JZ",     2, "code"),
       0x61                :  ("AJMP",   2, "code"),
       0x62                :  ("XRL",    2, "data A"),
       0x63                :  ("XRL",    3, "data immediate"),
       0x64                :  ("XRL",    2, "A immediate"),
       0x65                :  ("XRL",    2, "A data"),
       0x66                :  ("XRL",    1, "A, @R0"),
       0x67                :  ("XRL",    1, "A, @R1"),
       0x68                :  ("XRL",    1, "A, R0"),
       0x69                :  ("XRL",    1, "A, R1"),
       0x6A                :  ("XRL",    1, "A, R2"),
       0x6B                :  ("XRL",    1, "A, R3"),
       0x6C                :  ("XRL",    1, "A, R4"),
       0x6D                :  ("XRL",    1, "A, R5"),
       0x6E                :  ("XRL",    1, "A, R6"),
       0x6F                :  ("XRL",    1, "A, R7"),
       0x70                :  ("JNZ",    2, "code"),
       0x71                :  ("ACALL",  2, "code"),
       0x72                :  ("ORL",    2, "C bit"),
       0x73                :  ("JMP",    1, "@A+DPTR"),
       0x74                :  ("MOV",    2, "A immediate"),
       0x75                :  ("MOV",    3, "data immediate"),
       0x76                :  ("MOV",    2, "@R0 immediate"),
       0x77                :  ("MOV",    2, "@R1 immediate"),
       0x78                :  ("MOV",    2, "R0 immediate"),
       0x79                :  ("MOV",    2, "R1 immediate"),
       0x7A                :  ("MOV",    2, "R2 immediate"),
       0x7B                :  ("MOV",    2, "R3 immediate"),
       0x7C                :  ("MOV",    2, "R4 immediate"),
       0x7D                :  ("MOV",    2, "R5 immediate"),
       0x7C                :  ("MOV",    2, "R4 immediate"),
       0x7D                :  ("MOV",    2, "R5 immediate"),
       0x7E                :  ("MOV",    2, "R6 immediate"),
       0x7F                :  ("MOV",    2, "R7 immediate"),
       0x80                :  ("SJMP",   2, "code"),
       0x81                :  ("AJMP",   2, "code"),
       0x82                :  ("ANL",    2, "C bit"),
       0x83                :  ("MOVC",   1, "A, @A+PC"),
       0x84                :  ("DIV",    1, "AB"),
       0x85                :  ("MOV",    3, "data data"),
       0x86                :  ("MOV",    2, "data @R0"),
       0x87                :  ("MOV",    2, "data @R1"),
       0x88                :  ("MOV",    2, "data R0"),
       0x89                :  ("MOV",    2, "data R1"),
       0x8A                :  ("MOV",    2, "data R2"),
       0x8B                :  ("MOV",    2, "data R3"),
       0x8C                :  ("MOV",    2, "data R4"),
       0x8D                :  ("MOV",    2, "data R5"),
       0x8E                :  ("MOV",    2, "data R6"),
       0x8F                :  ("MOV",    2, "data R7"),
       0x90                :  ("MOV",    3, "DPTR immediate16"),
       0x91                :  ("ACALL",  2, "code"),
       0x92                :  ("MOV",    2, "bit C"),
       0x93                :  ("MOVC",   1, "A, @A+DPTR"),
       0x94                :  ("SUBB",   2, "A immediate"),
       0x95                :  ("SUBB",   2, "A data"),
       0x96                :  ("SUBB",   1, "A, @R0"),
       0x97                :  ("SUBB",   1, "A, @R1"),
       0x98                :  ("SUBB",   1, "A, R0"),
       0x99                :  ("SUBB",   1, "A, R1"),
       0x9A                :  ("SUBB",   1, "A, R2"),
       0x9B                :  ("SUBB",   1, "A, R3"),
       0x9C                :  ("SUBB",   1, "A, R4"),
       0x9D                :  ("SUBB",   1, "A, R5"),
       0x9E                :  ("SUBB",   1, "A, R6"),
       0x9F                :  ("SUBB",   1, "A, R7"),
       0xA0                :  ("ORL",    2, "C bit/"),
       0xA1                :  ("AJMP",   2, "code"),
       0xA2                :  ("MOV",    2, "C bit"),
       0xA3                :  ("INC",    1, "DPTR"),
       0xA4                :  ("MUL",    1, "AB"),
       0xA5                :  ("INVALID",1, ""), 
       0xA6                :  ("MOV",    2, "@R0 data"), 
       0xA7                :  ("MOV",    2, "@R1 data"), 
       0xA8                :  ("MOV",    2, "R0 data"), 
       0xA9                :  ("MOV",    2, "R1 data"), 
       0xAA                :  ("MOV",    2, "R2 data"), 
       0xAB                :  ("MOV",    2, "R3 data"), 
       0xAC                :  ("MOV",    2, "R4 data"), 
       0xAD                :  ("MOV",    2, "R5 data"), 
       0xAE                :  ("MOV",    2, "R6 data"), 
       0xAF                :  ("MOV",    2, "R7 data"), 
       0xB0                :  ("ANL",    2, "C bit/"), 
       0xB1                :  ("ACALL",  2, "code"), 
       0xB2                :  ("CPL",    2, "bit"), 
       0xB3                :  ("CPL",    2, "C"), 
       0xB4                :  ("CJNE",   3, "A immediate code"), 
       0xB5                :  ("CJNE",   3, "A data code"), 
       0xB6                :  ("CJNE",   3, "@R0 immediate code"), 
       0xB7                :  ("CJNE",   3, "@R1 immediate code"), 
       0xB8                :  ("CJNE",   3, "R0 immediate code"), 
       0xB9                :  ("CJNE",   3, "R1 immediate code"), 
       0xBA                :  ("CJNE",   3, "R2 immediate code"), 
       0xBB                :  ("CJNE",   3, "R3 immediate code"), 
       0xBC                :  ("CJNE",   3, "R4 immediate code"), 
       0xBD                :  ("CJNE",   3, "R5 immediate code"), 
       0xBE                :  ("CJNE",   3, "R6 immediate code"), 
       0xBF                :  ("CJNE",   3, "R7 immediate code"), 
       0xC0                :  ("PUSH",   2, "data"), 
       0xC1                :  ("AJMP",   2, "code"),
       0xC2                :  ("CLR",    2, "bit"),
       0xC3                :  ("CLR",    1, "C"),
       0xC4                :  ("SWAP",   1, "A"),
       0xC5                :  ("XCH",    2, "A data"),
       0xC6                :  ("XCH",    1, "A, @R0"),
       0xC7                :  ("XCH",    1, "A, @R1"),
       0xC8                :  ("XCH",    1, "A, R0"),
       0xC9                :  ("XCH",    1, "A, R1"),
       0xCA                :  ("XCH",    1, "A, R2"),
       0xCB                :  ("XCH",    1, "A, R3"),
       0xCC                :  ("XCH",    1, "A, R4"),
       0xCD                :  ("XCH",    1, "A, R5"),
       0xCE                :  ("XCH",    1, "A, R6"),
       0xCF                :  ("XCH",    1, "A, R7"),
       0xD0                :  ("POP",    2, "data"),
       0xD1                :  ("ACALL",  2, "code"),
       0xD2                :  ("SETB",   2, "bit"),
       0xD3                :  ("SETB",   1, "C"),
       0xD4                :  ("DA",     1, "A"),
       0xD5                :  ("DJNZ",   3, "data code"),
       0xD6                :  ("XCHD",   1, "A, @R0"),
       0xD7                :  ("XCHD",   1, "A, @R1"),
       0xD8                :  ("DJNZ",   2, "R0 code"),
       0xD9                :  ("DJNZ",   2, "R1 code"),
       0xDA                :  ("DJNZ",   2, "R2 code"),
       0xDB                :  ("DJNZ",   2, "R3 code"),
       0xDC                :  ("DJNZ",   2, "R4 code"),
       0xDD                :  ("DJNZ",   2, "R5 code"),
       0xDE                :  ("DJNZ",   2, "R6 code"),
       0xDF                :  ("DJNZ",   2, "R7 code"),
       0xE0                :  ("MOVX",   1, "A, @DPTR"),
       0xE1                :  ("AJMP",   2, "code"),
       0xE2                :  ("MOVX",   1, "A, @R0"),
       0xE3                :  ("MOVX",   1, "A, @R1"),
       0xE4                :  ("CLR",    1, "A"),
       0xE5                :  ("MOV",    2, "A data"),
       0xE6                :  ("MOV",    1, "A, @R0"),
       0xE7                :  ("MOV",    1, "A, @R1"),
       0xE8                :  ("MOV",    1, "A, R0"),
       0xE9                :  ("MOV",    1, "A, R1"),
       0xEA                :  ("MOV",    1, "A, R2"),
       0xEB                :  ("MOV",    1, "A, R3"),
       0xEC                :  ("MOV",    1, "A, R4"),
       0xED                :  ("MOV",    1, "A, R5"),
       0xEE                :  ("MOV",    1, "A, R6"),
       0xEF                :  ("MOV",    1, "A, R7"),
       0xF0                :  ("MOVX",   1, "@DPTR, A"),
       0xF1                :  ("ACALL",  2, "code"),
       0xF2                :  ("MOVX",   1, "@R0, A"),
       0xF3                :  ("MOVX",   1, "@R1, A"),
       0xF4                :  ("CPL",    1, "A"),
       0xF5                :  ("MOV",    2, "data A"),
       0xF6                :  ("MOV",    1, "@R0, A"),
       0xF7                :  ("MOV",    1, "@R1, A"),
       0xF8                :  ("MOV",    1, "R0, A"),
       0xF9                :  ("MOV",    1, "R1, A"),
       0xFA                :  ("MOV",    1, "R2, A"),
       0xFB                :  ("MOV",    1, "R3, A"),
       0xFC                :  ("MOV",    1, "R4, A"),
       0xFD                :  ("MOV",    1, "R5, A"),
       0xFE                :  ("MOV",    1, "R6, A"),
       0xFF                :  ("MOV",    1, "R7, A")
    }
    
    
    _OCD_DEBUG_SYNC = [0x5A, 0xA5, 0x01]
    _OCD_DEBUG_TYPE_PRAM_WRITE_4_BYTES_WITHOUT_ACK = 0x5C
    _OCD_DEBUG_TYPE_PRAM_WRITE_4_BYTES_WITH_ACK    = 0x5C | 1
    _OCD_DEBUG_TYPE_PRAM_WRITE_128_BYTES_WITH_ACK  = 0x5B
    
    _OCD_DEBUG_TYPE_PRAM_READ_4_BYTES  = 0x6D
    _OCD_DEBUG_TYPE_CPU_RESET_WITH_ACK = 0x4B
    
    _OCD_DEBUG_TYPE_PAUSE_ON_WITH_ACK  = 0x2D
    _OCD_DEBUG_TYPE_PAUSE_OFF_WITH_ACK = 0x3D
    
    _OCD_DEBUG_TYPE_READ_CPU_STATUS    = 0x2F
    
    _OCD_DEBUG_TYPE_COUNTER_CONFIG     = 0x6B
    
    _OCD_DEBUG_TYPE_BREAK_ON_WITH_ACK  = 0x7D
    _OCD_DEBUG_TYPE_BREAK_OFF_WITH_ACK = 0x1D
    
    _OCD_DEBUG_TYPE_RUN_PULSE_WITH_ACK = 0x49
    
    _OCD_DEBUG_TYPE_READ_DATA_MEM      = 0x6F; 
    _OCD_DEBUG_TYPE_WRITE_DATA_MEM     = 0x2B; 
    _OCD_DEBUG_TYPE_WRITE_DATA_MEM     = 0x2B; 
    _OCD_DEBUG_TYPE_UART_SEL           = 0x2A;
    
    _OCD_DEBUG_FRAME_REPLY_LEN = 12
    _OCD_SERIAL_TIME_OUT = 6
    
    _crc16_ccitt = CRC16_CCITT()
    
    _toggle = 0
    
    #========================================================================
    #  __init__
    #========================================================================
    
    def __init__ (self, com_port, baud_rate, verbose=0):
        self._serial = serial.Serial(com_port, baud_rate, timeout=OCD_8051._OCD_SERIAL_TIME_OUT)
        self._verbose = verbose
    
    #========================================================================
    #  _verify_crc
    #------------------------------------------------------------------------
    #  Remarks: calculate and check CRC16_CCITT for frames 
    #========================================================================
    def _verify_crc (self, data):
        data_list = [i for i in data]
        crc_data = OCD_8051._crc16_ccitt.get_crc (data_list [0 : OCD_8051._OCD_DEBUG_FRAME_REPLY_LEN - 2])
     
        if (crc_data == data_list [OCD_8051._OCD_DEBUG_FRAME_REPLY_LEN - 2 : OCD_8051._OCD_DEBUG_FRAME_REPLY_LEN]):
            return True
        else:
            return False
    
    #========================================================================
    #  code_mem_zero_fill_frame
    #========================================================================
    def code_mem_zero_fill_frame (self):
        frame = [0xFF, 0x00] * 64
        self._serial.write (frame)
    
    #========================================================================
    #  code_mem_write_32bit
    #========================================================================
    def code_mem_write_32bit (self, addr, data, ack=1, show_crc_error=0):
        addr_write_low_byte  = addr & 0xFF
        addr_write_high_byte = (addr >> 8) & 0xFF
        
        condition = True
        
        while (condition):
            data_in = data
            if (ack):
                frame_type_byte = OCD_8051._OCD_DEBUG_TYPE_PRAM_WRITE_4_BYTES_WITH_ACK * 2 + OCD_8051._toggle
            else:
                frame_type_byte = OCD_8051._OCD_DEBUG_TYPE_PRAM_WRITE_4_BYTES_WITHOUT_ACK * 2 + OCD_8051._toggle
            OCD_8051._toggle = 1 - OCD_8051._toggle
            
            frame = OCD_8051._OCD_DEBUG_SYNC + [frame_type_byte] + [addr_write_high_byte, addr_write_low_byte]
            for i in range(4):
                frame.append ((data_in >> 24) & 0xFF)
                data_in = data_in << 8
            frame = frame + OCD_8051._crc16_ccitt.get_crc (frame)
            self._serial.write (frame)
            
            if (self._verbose):
                print ("Ysend: ", [hex(i) for i in frame])
            
            if (ack):
                ret = self._serial.read (OCD_8051._OCD_DEBUG_FRAME_REPLY_LEN)
                condition = not self._verify_crc (ret)
                if (condition):
                    if (show_crc_error):
                        print ("\naddr=", addr, "Write 32bit reply CRC failed, Retry!")
                    self.code_mem_zero_fill_frame()
            else:
                condition = False    

    #========================================================================
    #  code_mem_write_128byte
    #========================================================================
    def code_mem_write_128byte (self, addr, data_list, show_crc_error=0):
    
        addr_write_low_byte  = addr & 0xFF
        addr_write_high_byte = (addr >> 8) & 0xFF
        
        condition = True
        #print ("wr128, addr = ", addr)
        
        while (condition):
            frame_type_byte = OCD_8051._OCD_DEBUG_TYPE_PRAM_WRITE_128_BYTES_WITH_ACK * 2 + OCD_8051._toggle
            OCD_8051._toggle = 1 - OCD_8051._toggle
            
            frame = OCD_8051._OCD_DEBUG_SYNC + [frame_type_byte] + [addr_write_high_byte, addr_write_low_byte]
            frame = frame + (data_list [0:4])
            frame = frame + OCD_8051._crc16_ccitt.get_crc (frame)
            frame = frame + data_list [4 : 128] + OCD_8051._crc16_ccitt.get_crc (data_list [4 : 128])
            
            self._serial.write (frame)
            
            if (self._verbose):
                print ("Xsend: ", [hex(i) for i in frame])
            
            ret = self._serial.read (OCD_8051._OCD_DEBUG_FRAME_REPLY_LEN)

            condition = not self._verify_crc (ret)
            if (condition):
                if (show_crc_error):
                    print ("\naddr=", addr, "Write 128byte reply CRC failed, Retry!")
                self.code_mem_zero_fill_frame()
            
    #========================================================================
    #  code_mem_read_32bit
    #========================================================================
    def code_mem_read_32bit (self, addr, show_crc_error=0):
    
        addr_write_low_byte  = addr & 0xFF
        addr_write_high_byte = (addr >> 8) & 0xFF
        
        condition = True
        
        #print ("read32bit, addr = ", addr)
        
        while (condition):
        
            frame_type_byte = OCD_8051._OCD_DEBUG_TYPE_PRAM_READ_4_BYTES * 2 + OCD_8051._toggle;
            OCD_8051._toggle = 1 - OCD_8051._toggle
            
            frame = OCD_8051._OCD_DEBUG_SYNC + [frame_type_byte] + [addr_write_high_byte, addr_write_low_byte]
            
            fill_data = 0x00FF00FF
            for i in range(4):
                frame.append ((fill_data >> 24) & 0xFF)
                fill_data = fill_data << 8
            frame = frame + OCD_8051._crc16_ccitt.get_crc (frame)
            
            if (self._verbose):
                print ("Asend: ", [hex(i) for i in frame])
            self._serial.write (frame)
            ret = self._serial.read (OCD_8051._OCD_DEBUG_FRAME_REPLY_LEN)
            
            condition = not self._verify_crc (ret)
            if (condition):
                if (show_crc_error):
                    print ("addr=", addr, "\nread 32bit reply CRC failed, Retry!")
                                
        if (self._verbose):
            print ("receive: ", [hex(i) for i in ret])
                
        return [i for i in ret[OCD_8051._OCD_DEBUG_FRAME_REPLY_LEN - 6 : OCD_8051._OCD_DEBUG_FRAME_REPLY_LEN - 2]]
        #print ([hex(i) for i in r])
    
    #========================================================================
    #  code_mem_write_byte
    #========================================================================
    def code_mem_write_byte (self, addr, data, ack=1):
        addr_word = addr // 4
        
        data_tmp = self.code_mem_read_32bit (addr_word * 4)
        data_tmp [addr % 4] = data
        data_word_tmp = (data_tmp[0] << 24) + (data_tmp[1] << 16) + (data_tmp[2] << 8) + (data_tmp[3])
        self.code_mem_write_32bit(addr, data_word_tmp, ack)

    #========================================================================
    #  code_mem_read_byte
    #========================================================================
    def code_mem_read_byte (self, addr):
        addr_word_aligned = (addr // 4) * 4
        data_tmp = self.code_mem_read_32bit (addr_word_aligned)
        
        data_byte = data_tmp [addr % 4]
        
        return data_byte
    
    #========================================================================
    #  data_mem_read_byte
    #========================================================================
    def data_mem_read_byte (self, addr, indirect1_direct0, show_crc_error=0):
        addr_write_low_byte  = addr & 0xFF
        addr_write_high_byte = (addr >> 8) & 0xFF
        
        condition = True
        
        while (condition):
        
            frame_type_byte = OCD_8051._OCD_DEBUG_TYPE_READ_DATA_MEM * 2 + OCD_8051._toggle;
            OCD_8051._toggle = 1 - OCD_8051._toggle
            
            frame = OCD_8051._OCD_DEBUG_SYNC + [frame_type_byte] + [addr_write_high_byte, addr_write_low_byte]
            
            fill_data = 0xFF00FF
            for i in range(3):
                frame.append ((fill_data >> 16) & 0xFF)
                fill_data = fill_data << 8
            
            frame.append (indirect1_direct0)            
            frame = frame + OCD_8051._crc16_ccitt.get_crc (frame)
            
            if (self._verbose):
                print ("Bsend: ", [hex(i) for i in frame])
            self._serial.write (frame)
            ret = self._serial.read (OCD_8051._OCD_DEBUG_FRAME_REPLY_LEN)
            
            condition = not self._verify_crc (ret)
            if (condition):
                if (show_crc_error):
                    print ("addr=", addr, "read data byte reply CRC fail")
                    
        if (self._verbose):
            print ("receive: ", [hex(i) for i in ret])
                 
        return ret[OCD_8051._OCD_DEBUG_FRAME_REPLY_LEN - 3]
    
    #========================================================================
    #  data_mem_write_byte
    #========================================================================
    def data_mem_write_byte (self, addr, data_byte, indirect1_direct0, show_crc_error=0):
        addr_write_low_byte  = addr & 0xFF
        addr_write_high_byte = (addr >> 8) & 0xFF
        
        condition = True
        
        while (condition):
        
            frame_type_byte = OCD_8051._OCD_DEBUG_TYPE_WRITE_DATA_MEM * 2 + OCD_8051._toggle;
            OCD_8051._toggle = 1 - OCD_8051._toggle
            
            frame = OCD_8051._OCD_DEBUG_SYNC + [frame_type_byte] + [addr_write_high_byte, addr_write_low_byte,data_byte, 0x12, 0x34, indirect1_direct0]
                               
            frame = frame + OCD_8051._crc16_ccitt.get_crc (frame)
            
            if (self._verbose):
                print ("Csend: ", [hex(i) for i in frame])
                
            self._serial.write (frame)
            ret = self._serial.read (OCD_8051._OCD_DEBUG_FRAME_REPLY_LEN)
            
            condition = not self._verify_crc (ret)
            if (condition):
                if (show_crc_error):
                    print ("addr=", addr, "write data byte reply CRC fail")
                    
        if (self._verbose):
            print ("receive: ", [hex(i) for i in ret])
                 
        return ret[OCD_8051._OCD_DEBUG_FRAME_REPLY_LEN - 3]
    
    #========================================================================
    #  cpu_reset
    #========================================================================
    def cpu_reset (self, show_crc_error=0):
    
        condition = True
        while (condition):
            frame_type_byte = OCD_8051._OCD_DEBUG_TYPE_CPU_RESET_WITH_ACK * 2 + OCD_8051._toggle;
            OCD_8051._toggle = 1 - OCD_8051._toggle
            
            frame = OCD_8051._OCD_DEBUG_SYNC + [frame_type_byte] + [0x12, 0x34, 0xab, 0xcd, 0xab, 0xcd]
            frame = frame + OCD_8051._crc16_ccitt.get_crc (frame)
            
            if (self._verbose):
                print ("Dsend: ", [hex(i) for i in frame])
            
            self._serial.write (frame)
            ret = self._serial.read (OCD_8051._OCD_DEBUG_FRAME_REPLY_LEN)
    
            condition = not self._verify_crc (ret)
            if (condition):
                if (show_crc_error):
                    print ("cpu reset reply CRC fail")
    
        if (self._verbose):
            print ("receive: ", [hex(i) for i in ret])

    #========================================================================
    #  cpu_pause
    #========================================================================
    def cpu_pause (self, on_off, no_reply=0, show_crc_error=0):
    
        condition = True
        while (condition):
        
            if (on_off):
                frame_type_byte = OCD_8051._OCD_DEBUG_TYPE_PAUSE_ON_WITH_ACK * 2 + OCD_8051._toggle;
            else:
                frame_type_byte = OCD_8051._OCD_DEBUG_TYPE_PAUSE_OFF_WITH_ACK * 2 + OCD_8051._toggle;
                
            OCD_8051._toggle = 1 - OCD_8051._toggle
            
            frame = OCD_8051._OCD_DEBUG_SYNC + [frame_type_byte] + [0x12, 0x34, 0xab, 0xcd, 0xab, 0xcd]
            frame = frame + OCD_8051._crc16_ccitt.get_crc (frame)
            
            if (self._verbose):
                print ("Esend: ", [hex(i) for i in frame])
            
            self._serial.write (frame)
            ret = self._serial.read (OCD_8051._OCD_DEBUG_FRAME_REPLY_LEN)
            
            if (no_reply):
                condition = 0
            else:
                condition = not self._verify_crc (ret)
            
            if (condition):
                if (show_crc_error):
                    print ("cpu pause reply CRC fail");
            
        if (self._verbose):
            print ("receive: ", [hex(i) for i in ret])

    #========================================================================
    #  read_cpu_status
    #========================================================================
    def read_cpu_status (self, show_crc_error=0):
    
        condition = True
        while (condition):
        
            frame_type_byte = OCD_8051._OCD_DEBUG_TYPE_READ_CPU_STATUS * 2 + OCD_8051._toggle;
            OCD_8051._toggle = 1 - OCD_8051._toggle
            
            frame = OCD_8051._OCD_DEBUG_SYNC + [frame_type_byte] + [0x12, 0x34, 0xab, 0xcd, 0xab, 0xcd]
            frame = frame + OCD_8051._crc16_ccitt.get_crc (frame)
            
            if (self._verbose):
                print ("Fsend: ", [hex(i) for i in frame])
            
            self._serial.write (frame)
            ret = self._serial.read (OCD_8051._OCD_DEBUG_FRAME_REPLY_LEN)
            
            condition = not self._verify_crc (ret)
            if (condition):
                if (show_crc_error):
                    print ("cpu read status reply CRC fail")
            
        ret_list = [i for i in ret]
        timer_counter = (ret_list [OCD_8051._OCD_DEBUG_FRAME_REPLY_LEN - 5]) + \
                        (ret_list [OCD_8051._OCD_DEBUG_FRAME_REPLY_LEN - 6] << 8) 
                        
        debug_counter = ((ret_list [OCD_8051._OCD_DEBUG_FRAME_REPLY_LEN - 7]) + \
                         (ret_list [OCD_8051._OCD_DEBUG_FRAME_REPLY_LEN - 8] << 8)) // 2
                        
        PC = ret_list [OCD_8051._OCD_DEBUG_FRAME_REPLY_LEN - 4] * 256 + ret_list [OCD_8051._OCD_DEBUG_FRAME_REPLY_LEN - 3]
        debug_stall_flag = ret_list [OCD_8051._OCD_DEBUG_FRAME_REPLY_LEN - 7] & 1 
                    
        if (self._verbose):
            print ("receive: ", [hex(i) for i in ret])
        
        self.debug_stall_flag = debug_stall_flag
        self.PC = PC
        self.debug_counter = debug_counter
        self.timer_counter = timer_counter

    #========================================================================
    #  counter_config
    #========================================================================
    def counter_config (self, debug_counter_reset, debug_counter_enable, timer_counter_reset, timer_counter_enable, show_crc_error=0):
        
        condition = True
        while (condition):
                
            frame_type_byte = OCD_8051._OCD_DEBUG_TYPE_COUNTER_CONFIG * 2 + OCD_8051._toggle;
            OCD_8051._toggle = 1 - OCD_8051._toggle
            
            tmp = (debug_counter_reset << 1) + \
                  (debug_counter_enable << 2) + \
                  (timer_counter_reset << 3) + \
                  (timer_counter_enable << 4)
                  
            frame = OCD_8051._OCD_DEBUG_SYNC + [frame_type_byte] + [0x12, 0x34, 0xab, 0xcd, 0xab, tmp]
            frame = frame + OCD_8051._crc16_ccitt.get_crc (frame)
            
            if (self._verbose):
                print ("Gsend: ", [hex(i) for i in frame])
            
            self._serial.write (frame)
            ret = self._serial.read (OCD_8051._OCD_DEBUG_FRAME_REPLY_LEN)
            
            condition = not self._verify_crc (ret)
            
            if (condition):
                if (show_crc_error):
                    print ("counter config reply CRC fail")
            
        if (self._verbose):
            print ("receive: ", [hex(i) for i in ret])
         
    #========================================================================
    #  set_breakpoint
    #========================================================================
    def set_breakpoint (self, break_addr_A, break_addr_B, show_crc_error=0):
    
        condition = True
        while (condition):

            frame_type_byte = OCD_8051._OCD_DEBUG_TYPE_BREAK_ON_WITH_ACK * 2 + OCD_8051._toggle;
            OCD_8051._toggle = 1 - OCD_8051._toggle
            
            break_addr_A_low_byte  = break_addr_A & 0xFF
            break_addr_A_high_byte = (break_addr_A >> 8) & 0xFF
            
            break_addr_B_low_byte  = break_addr_B & 0xFF
            break_addr_B_high_byte = (break_addr_B >> 8) & 0xFF
                    
            frame = OCD_8051._OCD_DEBUG_SYNC + [frame_type_byte] + [break_addr_A_high_byte, break_addr_A_low_byte, 0xab, 0xcd, break_addr_B_high_byte, break_addr_B_low_byte]
            frame = frame + OCD_8051._crc16_ccitt.get_crc (frame)
            
            if (self._verbose):
                print ("Hsend: ", [hex(i) for i in frame])
            
            self._serial.write (frame)
            ret = self._serial.read (OCD_8051._OCD_DEBUG_FRAME_REPLY_LEN)
            
            condition = not self._verify_crc (ret)
            if (condition):
                if (show_crc_error):
                    print ("set breakpoint reply CRC fail")
            
        if (self._verbose):
            print ("receive: ", [hex(i) for i in ret])

    #========================================================================
    #  breakpoint_off
    #========================================================================
    def breakpoint_off (self, show_crc_error=0):
    
        condition = True
        while (condition):

            frame_type_byte = OCD_8051._OCD_DEBUG_TYPE_BREAK_OFF_WITH_ACK * 2 + OCD_8051._toggle;
            OCD_8051._toggle = 1 - OCD_8051._toggle
                    
            frame = OCD_8051._OCD_DEBUG_SYNC + [frame_type_byte] + [0x12, 0x34, 0xab, 0xcd, 0x33, 0x99]
            frame = frame + OCD_8051._crc16_ccitt.get_crc (frame)
            
            if (self._verbose):
                print ("Isend: ", [hex(i) for i in frame])
            
            self._serial.write (frame)
            ret = self._serial.read (OCD_8051._OCD_DEBUG_FRAME_REPLY_LEN)
            
            condition = not self._verify_crc (ret)
            if (condition):
                if (show_crc_error):
                    print ("breakpoint off reply CRC fail")
            
        if (self._verbose):
            print ("receive: ", [hex(i) for i in ret])
    
    #========================================================================
    #  run_pulse
    #========================================================================
    def run_pulse (self, show_crc_error=0):
    
        condition = True
        while (condition):

            frame_type_byte = OCD_8051._OCD_DEBUG_TYPE_RUN_PULSE_WITH_ACK * 2 + OCD_8051._toggle;
            OCD_8051._toggle = 1 - OCD_8051._toggle
                    
            frame = OCD_8051._OCD_DEBUG_SYNC + [frame_type_byte] + [0x12, 0x34, 0xab, 0xcd, 0x33, 0x99]
            frame = frame + OCD_8051._crc16_ccitt.get_crc (frame)
            
            if (self._verbose):
                print ("Jsend: ", [hex(i) for i in frame])
            
            self._serial.write (frame)
            ret = self._serial.read (OCD_8051._OCD_DEBUG_FRAME_REPLY_LEN)
            
            condition = not self._verify_crc (ret)
            if (condition):
                if (show_crc_error):
                    print ("run pulse reply CRC fail")
            
        if (self._verbose):
            print ("receive: ", [hex(i) for i in ret])
    
    #========================================================================
    #  uart_select
    #========================================================================
    def uart_select (self, ocd0_cpu1):
    
        frame_type_byte = OCD_8051._OCD_DEBUG_TYPE_UART_SEL * 2 + OCD_8051._toggle;
        OCD_8051._toggle = 1 - OCD_8051._toggle
            
        frame = OCD_8051._OCD_DEBUG_SYNC + [frame_type_byte] + [0x12, 0x34, 0xab, 0xcd, 0xab, ocd0_cpu1*2]
        frame = frame + OCD_8051._crc16_ccitt.get_crc (frame)
            
        if (self._verbose):
            print ("send: ", [hex(i) for i in frame])
            
        self._serial.write (frame)
        
        
#============================================================================
#  main
#============================================================================
   
def main():

    print ("=================================================================") 
    ocd = OCD_8051 ("COM4", 115200)
   
    while True:
         if (ocd._serial.in_waiting):
            r = ocd._serial.read (ocd._serial.in_waiting)  
            prt_out = ""
            for i in r:
                prt_out = prt_out + chr(i) 
            print (prt_out, end="")
            sys.stdout.flush()
     
    
if __name__ == "__main__":
    main()        

