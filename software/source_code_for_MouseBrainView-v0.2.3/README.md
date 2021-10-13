# Project 45340

## GUI
Client with graphical interface is located in GUI/ directory.  
To build it you need the following pachages:  
- Python 3.7
- lib PyQt5 5.12.3
- lib PyQtGraph 0.11.1
- lib numpy 1.19.5
- pyinstaller 4.2
- pyrcc5 5.12.3
  
To run this program go to "GUI/build" directory and run the following command
```
make run
```
To build binary file just execute "make" without "run"
```
make
```
This command will build static binary file which can be used on other PC without python working environment.  

By default makefile uses "python3" for python 3 and "pyrcc5" for pyrcc5.  
If your working environment uses different names for that programs you can change python3 and pyrcc5 names by setting environment variables PP3 and RCC5 respectively.  
Example:
```
C:\msys64\usr\bin\make PP3=python RCC5=C:\Users\owner\anaconda3\Library\bin\pyrcc5.bat run
```

