import re
import json
with open("permissions.json", "r", encoding="utf-8") as file:
    text = json.loads(file.read())
permissions = {
    "ohos.permission.LOCATION_IN_BACKGROUND": "位置信息",
    "ohos.permission.LOCATION": "位置信息",
    "ohos.permission.APPROXIMATELY_LOCATION": "位置信息",
    "ohos.permission.CAMERA": "相机",
    "ohos.permission.MICROPHONE": "麦克风",
    "ohos.permission.READ_CALENDAR": "日历",
    "ohos.permission.WRITE_CALENDAR": "日历",
    "ohos.permission.READ_WHOLE_CALENDAR": "日历",
    "ohos.permission.WRITE_WHOLE_CALENDAR": "日历",
    "ohos.permission.ACTIVITY_MOTION": "健身运动",
    "ohos.permission.READ_HEALTH_DATA": "身体传感器",
    "ohos.permission.DISTRIBUTED_DATASYNC": "多设备协同",
    "ohos.permission.ANSWER_CALL": "电话",
    "ohos.permission.MANAGE_VOICEMAIL": "电话",
    "ohos.permission.READ_CONTACTS": "通讯录",
    "ohos.permission.WRITE_CONTACTS": "通讯录",
    "ohos.permission.READ_CALL_LOG": "通话记录",
    "ohos.permission.WRITE_CALL_LOG": "通话记录",
    "ohos.permission.READ_CELL_MESSAGES": "信息",
    "ohos.permission.READ_MESSAGES": "信息",
    "ohos.permission.RECEIVE_MMS": "信息",
    "ohos.permission.RECEIVE_SMS": "信息",
    "ohos.permission.RECEIVE_WAP_MESSAGES": "信息",
    "ohos.permission.SEND_MESSAGES": "信息",
    "ohos.permission.WRITE_AUDIO": "音乐和音频",
    "ohos.permission.READ_AUDIO": "音乐和音频",
    "ohos.permission.READ_DOCUMENT": "文件",
    "ohos.permission.WRITE_DOCUMENT": "文件",
    "ohos.permission.READ_MEDIA": "文件",
    "ohos.permission.WRITE_MEDIA": "文件",
    "ohos.permission.WRITE_IMAGEVIDEO": "图片和视频",
    "ohos.permission.READ_IMAGEVIDEO": "图片和视频",
    "ohos.permission.MEDIA_LOCATION": "图片和视频",
    "ohos.permission.APP_TRACKING_CONSENT": "广告跟踪",
    "ohos.permission.GET_INSTALLED_BUNDLE_LIST": "读取已安装应用列表",
    "ohos.permission.ACCESS_BLUETOOTH": "蓝牙",
    "ohos.permission.SECURE_PASTE": "剪贴板",
    "ohos.permission.READ_PASTEBOARD": "剪贴板"
}
result = {}
for item in text:
    name = item['name']
    item.pop('name')
    result[name] = item
    if name in permissions:
        result[name]['group'] = permissions[name]
json_data = json.dumps(result, indent=4, ensure_ascii=False)
with open("permissions.json", "w", encoding="utf-8") as file:
    file.write(json_data)