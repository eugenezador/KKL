APP_DIR=app/

pyinstaller src/QCL.py --onefile --distpath $APP_DIR

cp src/angles.txt $APP_DIR
cp src/settings_default.txt $APP_DIR
cp src/wave_numbers.txt $APP_DIR