@echo off
cd /d D:\Users\daphnefan\Desktop\student_monitor

call venv\Scripts\activate

python .\scripts\unidays_monitor.py --run
python .\scripts\studentbeans_monitor.py --run
python .\scripts\build_dashboard.py
python .\scripts\build_ios26_preview.py

cd /d D:\Users\daphnefan\Desktop\git_monitor

copy /Y D:\Users\daphnefan\Desktop\student_monitor\docs\index.html docs\index.html
copy /Y D:\Users\daphnefan\Desktop\student_monitor\docs\dashboard_*.html docs\

git add docs
git commit -m "Daily dashboard update"
git push

exit
