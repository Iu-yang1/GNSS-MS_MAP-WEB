from time import sleep
import serial
import re
import time
import json
import smbus
import math

utctime = ''
lat = ''
ulat = ''
lon = ''
ulon = ''
numSv = ''
msl = ''
cogt = ''
cogm = ''
sog = ''
kph = ''
gps_t = 0


ser = serial.Serial("/dev/ttyUSB0", 115200)

if ser.isOpen():
    print("串口打开成功! 波特率=9600")
else:
    print("串口打开失败!")


bus = smbus.SMBus(1)


ACCEL_ADDRESS = 0x19  
MAG_ADDRESS = 0x1E    


bus.write_byte_data(ACCEL_ADDRESS, 0x20, 0x27)  # CTRL_REG1_A: 0x20, Value: 0x27 (10Hz, XYZ enable)


bus.write_byte_data(MAG_ADDRESS, 0x02, 0x00)  # MR_REG_M: 0x02, Value: 0x00 (Continuous conversion mode)
bus.write_byte_data(MAG_ADDRESS, 0x00, 0x10)  # CRA_REG_M: 0x00, Value: 0x10 (15Hz output rate)


ACCEL_SCALE_MODIFIER_2G = 16384.0
GRAVITY = 9.7920  

# 互补滤波器参数
alpha = 0.98  # 滤波系数
dt = 0.1     # 时间间隔，单位：秒


heading_filtered = 0.0

def read_accel_data():
    # 读取加速度数据
    data = bus.read_i2c_block_data(ACCEL_ADDRESS, 0x28 | 0x80, 6)
    x = data[0] | (data[1] << 8)
    y = data[2] | (data[3] << 8)
    z = data[4] | (data[5] << 8)
    if x > 32767: x -= 65536
    if y > 32767: y -= 65536
    if z > 32767: z -= 65536
    return x, y, z

def read_mag_data():
    # 读取地磁数据
    data = bus.read_i2c_block_data(MAG_ADDRESS, 0x03, 6)
    x = data[0] << 8 | data[1]
    z = data[2] << 8 | data[3]
    y = data[4] << 8 | data[5]
    if x > 32767: x -= 65536
    if y > 32767: y -= 65536
    if z > 32767: z -= 65536
    return x, y, z

def Convert_to_degrees(in_data1, in_data2):

    print(in_data1,in_data2)
    data1=int(str(in_data1)[0:-2])+((float(str(in_data1)[-2:]+'.'+str(in_data2))/60))
    
    return data1
    
    len_data1 = len(in_data1)
    str_data2 = "%05d" % int(in_data2)
    temp_data = int(in_data1)
    symbol = 1
    if temp_data < 0:
        symbol = -1
    degree = int(temp_data / 100.0)
    str_decimal = str(in_data1[len_data1-2]) + str(in_data1[len_data1-1]) + str(str_data2)
    f_degree = int(str_decimal) / 60.0 / 100000.0
    if symbol > 0:
        result = degree + f_degree
    else:
        result = degree - f_degree
    return result

def Convert_to_dms(degrees):
    
    d = int(degrees)
    md = abs(degrees - d) * 60
    m = int(md)
    s = (md - m) * 60
    return f"{d}°{m}'{s:.2f}\""

def parse_GGA(GGA):
    
    GGA_g = re.findall(r"\w+(?=,)|(?<=,)\w+", str(GGA))
    if len(GGA_g) < 13:
        print("BDS未找到")
        return False
    else:
        global utctime, lat, ulat, lon, ulon, numSv, msl, gps_t
        utctime = GGA_g[0]
        lat = "%.8f" % Convert_to_degrees(str(GGA_g[2]), str(GGA_g[3]))
        ulat = GGA_g[4]
        lon = "%.8f" % Convert_to_degrees(str(GGA_g[5]), str(GGA_g[6]))
        ulon = GGA_g[7]
        numSv = GGA_g[9]
        msl = GGA_g[12] + '.' + GGA_g[13] + GGA_g[14]
        gps_t = 1
        return True

def parse_VTG(VTG):
    
    VTG_g = re.findall(r"\w+(?=,)|(?<=,)\w+", str(VTG))
    global cogt, cogm, sog, kph
    cogt = VTG_g[0] + '.' + VTG_g[1] + 'T'
    if VTG_g[3] == 'M':
        cogm = '0.00'
        sog = VTG_g[4] + '.' + VTG_g[5]
        kph = VTG_g[7] + '.' + VTG_g[8]
    else:
        cogm = VTG_g[3] + '.' + VTG_g[4]
        sog = VTG_g[6] + '.' + VTG_g[7]
        kph = VTG_g[9] + '.' + VTG_g[10]

def GPS_read():
    
    global gps_t
    if True or ser.inWaiting():
        if  ser.read(1) == b'G':
            if  ser.inWaiting() and ser.read(1) == b'N':
                if True or  ser.inWaiting():
                    choice = ser.read(1)
                    if  choice == b'G' and ser.inWaiting() and ser.read(1) == b'G':
                        if  ser.inWaiting() and ser.read(1) == b'A':
                            GGA = ser.read(70)
                            print(GGA)
                            return parse_GGA(GGA)                          
    return False

def write_to_json(data):
    
    with open('/data/gps_imu_data.json', 'w') as json_file:
        json.dump(data, json_file, indent=4)

try:
    a = 0
    while True:
        
        if GPS_read():
            # 读取加速度计数据
            xAccel, yAccel, zAccel = read_accel_data()

            # 转换为g
            xAccel_g = xAccel / ACCEL_SCALE_MODIFIER_2G
            yAccel_g = yAccel / ACCEL_SCALE_MODIFIER_2G
            zAccel_g = zAccel / ACCEL_SCALE_MODIFIER_2G

            # 读取地磁数据
            xMag, yMag, zMag = read_mag_data()

            # 计算原始航向角（未经过加速度计矫正）
            heading_raw = math.atan2(yMag, xMag)
            if heading_raw < 0:
                heading_raw += 2 * math.pi
            if heading_raw > 2 * math.pi:
                heading_raw -= 2 * math.pi
            heading_raw_degrees = heading_raw * 180 / math.pi

            # 计算俯仰角和横滚角
            pitch = math.atan2(yAccel_g, math.sqrt(xAccel_g * xAccel_g + zAccel_g * zAccel_g))
            roll = math.atan2(-xAccel_g, zAccel_g)

            # 校正磁力计数据
            xMag_h = xMag * math.cos(pitch) + zMag * math.sin(pitch)
            yMag_h = xMag * math.sin(roll) * math.sin(pitch) + yMag * math.cos(roll) - zMag * math.sin(roll) * math.cos(pitch)

            # 计算校正后的航向角
            heading = math.atan2(yMag_h, xMag_h)
            if heading < 0:
                heading += 2 * math.pi
            if heading > 2 * math.pi:
                heading -= 2 * math.pi
            headingDegrees = heading * 180 / math.pi

            
            heading_filtered = alpha * (heading_filtered + dt * (headingDegrees - heading_filtered)) + (1 - alpha) * headingDegrees

            # 转换加速度为m/s²
            xAccel_ms2 = xAccel_g * GRAVITY
            yAccel_ms2 = yAccel_g * GRAVITY
            zAccel_ms2 = zAccel_g * GRAVITY

            
            data = {
                "utc_time": utctime,
                "latitude": f"{lat} {ulat}",
                "longitude": f"{lon} {ulon}",
                "latitude_dms": Convert_to_dms(float(lat)),
                "longitude_dms": Convert_to_dms(float(lon)),
                "number_of_satellites": numSv,
                "altitude": f"{msl}",
                "true_north_heading": f"{cogt}°",
                "magnetic_north_heading": f"{cogm}°",
                "ground_speed_kn": sog,
                "ground_speed_kph": kph,
                "x_accel_ms2": xAccel_ms2,
                "y_accel_ms2": yAccel_ms2,
                "z_accel_ms2": zAccel_ms2,
                "heading_raw_degrees": heading_raw_degrees,
                "heading_filtered_degrees": heading_filtered
            }

            write_to_json(data)
            print("*********************")
            print(f"UTC时间: {utctime}")
            print(f"纬度: {lat} {ulat} (十进制度) / {Convert_to_dms(float(lat))} (度分秒)")
            print(f"经度: {lon} {ulon} (十进制度) / {Convert_to_dms(float(lon))} (度分秒)")
            print(f"卫星数量: {numSv}")
            print(f"海拔: {msl} 米")
            print(f"真北航向: {cogt}°")
            print(f"磁北航向: {cogm}°")
            print(f"地速: {sog} Kn")
            print(f"地速: {kph} Km/h")
            print(f"X轴加速度: {xAccel_ms2} m/s²")
            print(f"Y轴加速度: {yAccel_ms2} m/s²")
            print(f"Z轴加速度: {zAccel_ms2} m/s²")
            print(f"原始航向角: {heading_raw_degrees}°")
            print(f"滤波后航向角: {heading_filtered}°")
            print("*********************")
            a += 1
            print(f"读取计数: {a}")
except KeyboardInterrupt:
    ser.close()
    print("串口已关闭!")