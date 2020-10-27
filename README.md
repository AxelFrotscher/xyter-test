# XYTER - Test Github Repository

The XYTER test suite is written entirely in Python, and depends on ROOT.

![ENC Test board](front-test-board.jp2)

## Quick Start

1. open a new session on the PC: ag-ob-strasse (this will automatically source _/home/ststest/cbmsoft/ipbuslogin.sh_)
2. Navigate to _/home/ststest/cbmsoft/python_ipbus/run/sts/asicTest_. This is important, as many of the scripts rely on relative pathes
3. Initialize the connection to the AFCK board and the FEB-C card _sh arun.sh_

### Calibration of the Channels
Each of the 128 Channels has 31 ADC and 1 TDC comparator, which can be tuned individually, using the TRIM values. To get a new calibration, run _python trim_sts.py_

### S-Curves 
To get the S-Curve of a specific channel run _python scurve_sts.py [edpb_id] [afck_id] [channel number]_, where edpb_id and afck_id are 0.

### Acquiring Data
To acquire data with the current settings, run _python saveRawData.py 0 0 [length in seconds]_.

### Getting ENC values
To get the ENC values of all channels, run _python fast_enc_noise.py_. For a single channel use _python single_fast_enc_noise.py [channel number]_.

### References

Many Pictures, as well the XYTER manual and the CBM Progress Reports can be found at the [STRASSE Wiki](https://www.strasse.tu-darmstadt.de/Electronics) 
