@echo off
chcp 65001
echo ========================================================
echo        科研课题申报智能体 - 每日定时任务执行脚本
echo ========================================================

:: 切换到脚本所在目录
cd /d "%~dp0"

:: 记录开始时间
echo [开始时间] %date% %time% >> data\schedule_log.txt
echo 正在执行政策爬取与分析流程，请稍候...

:: ==============================================
:: 配置虚拟环境（如果使用的话，取消下面两行的注释并修改路径）
:: echo 正在激活虚拟环境...
:: call venv\Scripts\activate
:: ==============================================

:: 执行主程序
python main.py >> data\schedule_log.txt 2>&1

:: 检查执行结果
if %errorlevel% equ 0 (
    echo [执行成功] 任务已顺利完成！ >> data\schedule_log.txt
    echo ✅ 任务执行完成！日志已保存至 data\schedule_log.txt
) else (
    echo [执行失败] 错误码: %errorlevel% >> data\schedule_log.txt
    echo ❌ 任务执行出现异常，请查看 data\schedule_log.txt
)

echo [结束时间] %date% %time% >> data\schedule_log.txt
echo ========================================================

:: 如果不需要暂停看输出，可以把下面的 pause 注释掉
:: 建议在 Windows 任务计划程序中运行时注释掉 pause
pause
