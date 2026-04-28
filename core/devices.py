import sounddevice as sd

def get_unique_input_devices():
    devices = []
    seen_names = set()
    for i, dev in enumerate(sd.query_devices()):
        if dev['max_input_channels'] == 0:
            continue
        base_name = dev['name'].split('(')[0].strip().lower()
        if base_name in seen_names:
            continue
        seen_names.add(base_name)
        devices.append((i, dev['name'], dev['max_input_channels']))
    return devices

def get_device_channels(device_id):
    try:
        info = sd.query_devices(device_id)
        return info['max_input_channels']
    except:
        return 0