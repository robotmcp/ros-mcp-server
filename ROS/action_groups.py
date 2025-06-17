#!/usr/bin/env python
# -*- coding: utf-8 -*-

import rospy
import os
from std_msgs.msg import String

class ActionGroupsPublisher:
    def __init__(self):
        # Инициализация ноды
        rospy.init_node('action_groups_publisher')
        
        # Путь к папке с данными
        self.folder_path = "/home/ubuntu/software/ainex_controller/ActionGroups"
        
        # Создаем publisher для топика /action_groups_data
        self.pub = rospy.Publisher('/action_groups_data', String, queue_size=10)
        
        # Таймер для периодической публикации (раз в секунду)
        rospy.Timer(rospy.Duration(1), self.publish_data)
        
        rospy.loginfo("ActionGroups Publisher запущен и публикует данные в /action_groups_data")

    def publish_data(self, event):
        try:
            # Получаем список файлов в папке
            files = os.listdir(self.folder_path)
            
            # Формируем строку с данными
            data = "ActionGroups: " + ", ".join(files)
            
            # Публикуем данные
            self.pub.publish(data)
            
        except Exception as e:
            rospy.logerr("Ошибка при чтении папки: %s", str(e))

if __name__ == '__main__':
    try:
        ActionGroupsPublisher()
        rospy.spin()
    except rospy.ROSInterruptException:
        pass