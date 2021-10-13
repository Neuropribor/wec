#-------------------------------------------------------------------------------
# author:	Nikita Makarevich
# email:	nikita.makarevich@spbpu.com
# 2021
#-------------------------------------------------------------------------------
# Mouse Brain View
#-------------------------------------------------------------------------------

# C:\msys64\usr\bin\make PP3=python RCC5=C:\Users\owner\anaconda3\Library\bin\pyrcc5.bat run

PP3 = python3
RCC5 = pyrcc5

VER = "0.2.3"

targ: ../main.py MainForm.py res.py
	pyinstaller --windowed --icon=../forms/window_image.ico --name "MouseBrainView-v$(VER)" ../main.py

run: ../main.py MainForm.py res.py
	$(PP3) ../main.py

MainForm.py: ../forms/MainForm.ui res.py
	$(PP3) -m PyQt5.uic.pyuic ../forms/MainForm.ui -o MainForm.py -x --resource-suffix=''
res.py: ../forms/res.qrc
	$(RCC5) -o res.py ../forms/res.qrc
	#$(RCC5) -o ../res.py ../forms/res.qrc
