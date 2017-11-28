# M10_high_speed_config_software
M10 high speed configuration utility

For Window:
    Use the .exe file in the bin directory directly
    
For Linux Support:

The following is tested with Ubuntu 17.1

1) Install Python 3

    sudo apt install python3
    
2) Install Python 3 pip

    sudo apt install python3-pip

3) Install Python 3 tk

    sudo apt install python3-tk

4) Install Pmw

    pip3 install Pmw

5) Install pySerial

    pip3 install pySerial

6) Install getch

    pip3 install getch
    
7) Install Linux driver for FT232R if necessary, as shown in 
    [Application Note AN_220, FTDI Drivers Installation Guide for Linux](http://www.ftdichip.com/Support/Documents/AppNotes/AN_220_FTDI_Drivers_Installation_Guide_for_Linux.pdf)
    
8) add username to the dialout group. Otherwise the serial port will be under the monopoly of root

    sudo adduser USERNAME dialout
    
9) Now type in python3 M10_config_gui.py to launch the utility GUI

