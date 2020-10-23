# --------------------------------------------------------------------
# SCA related constants
# channels, commands, special data
# note: incomplete list, some commands and channels not yet included
#  - information derived mostly from SCA manual rev.8.2
#  - some additions taken from rev.6.2
#  - J.L. Dec.2017
#
#  some more EC related info:
#  - bytes are transmitted LSBit first
#  - data is transmitted [23..16, 31..24, 7..0, 15..8]
#  - CRC is CRC16: polynomial 0x1021, initial value 0xffff, input reflected, result reflected, final xor 0x0
#     Example: 0x000e0200040200ff0000 gives CRC 0x8cea
#  - CRC is calculated with data byte in transfer order
#  - CRC is transmitted LSByte first 
#  - HDLC P/F not implemented and always 0
#
# --------------------------------------------------------------------


# -----------------------------------------------------------------
# --- SCA channels ------------------------------------------------ 
# -----------------------------------------------------------------
SCA_CH_CTRL = 0x00
SCA_CH_SPI = 0x01
SCA_CH_GPIO = 0x02
SCA_CH_I2C0 = 0x03
SCA_CH_I2C1 = 0x04
SCA_CH_I2C2 = 0x05
SCA_CH_I2C3 = 0x06
SCA_CH_I2C4 = 0x07
SCA_CH_I2C5 = 0x08
SCA_CH_I2C6 = 0x09
SCA_CH_I2C7 = 0x0a
SCA_CH_I2C8 = 0x0b
SCA_CH_I2C9 = 0x0c
SCA_CH_I2CA = 0x0d
SCA_CH_I2CB = 0x0e
SCA_CH_I2CC = 0x0f
SCA_CH_I2CD = 0x10
SCA_CH_I2CE = 0x11
SCA_CH_I2CF = 0x12
SCA_CH_JTAG = 0x13
SCA_CH_ADC = 0x14
SCA_CH_DAC = 0x15

SCA_CH_ID = 0x14  # documented under "CTRL", but uses ADC channel
SCA_CH_SEU = 0x13  # documented under "CTRL", but uses JTAG channel

# -----------------------------------------------------------------
# --- SCA commands and data ---------------------------------------
# ---   sorted by channel   ---------------------------------------
# -----------------------------------------------------------------

# --- CTRL channel --------------------------------------
SCA_CTRL_W_CRB = 0x02
SCA_CTRL_W_CRC = 0x04
SCA_CTRL_W_CRD = 0x06
SCA_CTRL_R_CRB = 0x03
SCA_CTRL_R_CRC = 0x05
SCA_CTRL_R_CRD = 0x07

SCA_CTRL_R_ID_V2 = 0xd1
SCA_CTRL_R_ID_V1 = 0x91
SCA_CTRL_R_SEU = 0xf1
SCA_CTRL_C_SEU = 0xf0

SCA_CTRL_W_CURR = 0x00  # Elink Tx current write. Implemented in V2? Only documented in rev.6.2
SCA_CTRL_R_CURR = 0x01  # Elink Tx current read.  Implemented in V2? Only documented in rev.6.2

# --- channel enable --------------------- 
SCA_CTRL_CRB_ENGPIO = 0x04000000
SCA_CTRL_CRB_ENI2C0 = 0x08000000
SCA_CTRL_CRB_ENI2C1 = 0x10000000
SCA_CTRL_CRB_ENI2C2 = 0x20000000
SCA_CTRL_CRB_ENI2C3 = 0x40000000
SCA_CTRL_CRB_ENI2C4 = 0x80000000

SCA_CTRL_CRD_ENJTAG = 0x08000000
SCA_CTRL_CRD_ENADC = 0x10000000
SCA_CTRL_CRD_ENDAC = 0x20000000
# ----------------------------------------
SCA_CTRL_DATA_R_ID = 0x00000001  # data word to be sent for reading device ID (V2)

# --- GPIO channel ----------------------------------------
SCA_GPIO_W_DATAOUT = 0x10
SCA_GPIO_W_DIRECTION = 0x20
SCA_GPIO_W_INTSEL = 0x30
SCA_GPIO_W_INTTRIG = 0x40
SCA_GPIO_W_INTENABLE = 0x60
SCA_GPIO_W_INTS = 0x70
SCA_GPIO_W_CLKSEL = 0x80
SCA_GPIO_W_EDGESEL = 0x90

SCA_GPIO_R_DATAIN = 0x01
SCA_GPIO_R_DATAOUT = 0x11
SCA_GPIO_R_DIRECTION = 0x21
SCA_GPIO_R_INTSEL = 0x31
SCA_GPIO_R_INTTRIG = 0x31
SCA_GPIO_R_INTENABLE = 0x61
SCA_GPIO_R_INTS = 0x71
SCA_GPIO_R_CLKSEL = 0x81
SCA_GPIO_R_EDGESEL = 0x81

# --- ADC channel (SCA V2) --------------------------------
SCA_ADC_W_CURR = 0x60
SCA_ADC_W_MUX = 0x50
SCA_ADC_GO = 0x02
SCA_ADC_R_DATA = 0x21
SCA_ADC_R_RAW = 0x31
SCA_ADC_R_MUX = 0x51

# --- ADC channel (SCA V1) --------------------------------
SCAV1_ADC_W_INSEL = 0x30
SCAV1_ADC_GO = 0xB2  # Note: does NOT return conversion value (tested with V1)
SCAV1_ADC_R_DATA = 0x51  # Note: only R_DATA returns the conversion value (tested with V1)
SCAV1_ADC_R_INSEL = 0x31
SCAV1_ADC_W_CUREN = 0x40
SCAV1_ADC_R_CUREN = 0x41
SCAV1_ADC_W_CTRL = 0x10
SCAV1_ADC_R_CTRL = 0x11

# --- DAC channel ------------------------------------------
# read and write 8 bit DAC values to DAC A,B,C,D
# note: uses data bits[31..24], at least in V1
SCA_DAC_W_A = 0x10  # DAC0
SCA_DAC_W_B = 0x20
SCA_DAC_W_C = 0x30
SCA_DAC_W_D = 0x40  # DAC3

SCA_DAC_R_A = 0x11
SCA_DAC_R_B = 0x21
SCA_DAC_R_C = 0x31
SCA_DAC_R_D = 0x41

# --- I2C channels ------------------------------------------
# regs:
#       MASK
#       CTRL = SCLMODE, NBYTE[4..0], FREQ[1..0]
#       STATUS
#       DATA
SCA_I2C_W_MSK = 0x20
SCA_I2C_W_CTRL = 0x30
SCA_I2C_W_DATA0 = 0x40
SCA_I2C_W_DATA1 = 0x50
SCA_I2C_W_DATA2 = 0x60
SCA_I2C_W_DATA3 = 0x70

SCA_I2C_R_MSK = 0x21
SCA_I2C_R_CTRL = 0x31
SCA_I2C_R_DATA0 = 0x41
SCA_I2C_R_DATA1 = 0x51
SCA_I2C_R_DATA2 = 0x61
SCA_I2C_R_DATA3 = 0x71

SCA_I2C_R_STR = 0x11

SCA_I2C_M_7B_W = 0xda  # START multi byte write using 7b addressing
SCA_I2C_M_7B_R = 0xde  # START multi byte read using 7b addressing
SCA_I2C_S_7B_W = 0x82  # START single byte write using 7b addressing
SCA_I2C_S_7B_R = 0x86  # START single byte read using 7b addressing
SCA_I2C_M_10B_W = 0xe2  # START multi byte write using 10b addressing
SCA_I2C_M_10B_R = 0xe6  # START multi byte read using 10b addressing
SCA_I2C_S_10B_W = 0x8a  # START single byte write using 10b addressing
SCA_I2C_S_10B_R = 0x8e  # START single byte read using 10b addressing

SCA_I2C_SPEED_100 = 0x0
SCA_I2C_SPEED_200 = 0x1
SCA_I2C_SPEED_400 = 0x2
SCA_I2C_SPEED_1000 = 0x3

# --- JTAG channel ------------------------------------------
#    not yet implemented


# --- SPI channel -------------------------------------------
#    not yet implemented
