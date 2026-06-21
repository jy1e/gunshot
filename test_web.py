from stage4_driver import WebAppDriver
import time

driver = WebAppDriver(
    base_url='file:///C:/Users/daame/Desktop/gunshot/02_testboard.html',
    browser='chrome'
)

driver.send_command('go_to_board')
driver.send_command('write_post')
time.sleep(1)

# JavaScript로 홈 버튼 강제 클릭
d = driver.driver
d.execute_script("goToBoard()") if hasattr(d, 'execute_script') else None
d.execute_script("goToList()")
time.sleep(1)

print('cancel_write:', driver.send_command('cancel_write'))
time.sleep(1)
print('go_to_home:', driver.send_command('go_to_home'))
driver.close()