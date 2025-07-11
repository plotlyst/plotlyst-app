#!/bin/bash

# exit when any command fails
set -e

pip uninstall -y qt-uic
pip uninstall -y qt-menu
pip uninstall -y qt-handy
pip uninstall -y qt-anim
pip uninstall -y qt-tour
pip uninstall -y qt-textedit
pip uninstall -y qt-emojipicker
pip uninstall -y qt-frames
pip uninstall -y qt-toolbox

pip install git+https://github.com/plotlyst/qt-uic.git
pip install git+https://github.com/plotlyst/qt-menu.git
pip install git+https://github.com/plotlyst/qt-handy.git
pip install git+https://github.com/plotlyst/qt-anim.git
pip install git+https://github.com/plotlyst/qt-tour.git
pip install git+https://github.com/plotlyst/qt-textedit.git
pip install git+https://github.com/plotlyst/qt-emojipicker.git
pip install git+https://github.com/plotlyst/qt-frames.git
pip install git+https://github.com/plotlyst/qt-toolbox-widget.git
