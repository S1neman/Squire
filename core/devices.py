import sounddevice as sd

def get_default_input_device():
    default_idx = sd.default.device[0]
    if default_idx is None:
        return None, None
    try:
        dev = sd.query_devices(default_idx)
        if dev['max_input_channels'] > 0:
            return default_idx, dev['name']
    except:
        pass
    return None, None

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