@echo off
cd /d D:\Users\daphnefan\Desktop\git_monitor

copy /Y D:\Users\daphnefan\Desktop\student_monitor\docs\index.html docs\index.html
copy /Y D:\Users\daphnefan\Desktop\student_monitor\docs\dashboard_*.html docs\

git add docs
git commit -m "Update dashboard"
git push
