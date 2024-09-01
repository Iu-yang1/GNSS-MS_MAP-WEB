<!DOCTYPE html>
<html lang="zh">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>GNSS+IMU</title>
    <style>
        body {
            margin: 0;
            padding: 0;
            font-family: Arial, sans-serif;
            text-align: center;
            position: relative;
        }
        .info-container, .time-container, .weather-container {
            position: absolute;
            padding: 10px;
            font-size: 1.0em;
            color: blue;
            background: rgba(255, 255, 255, 0.1);
            border: 1px solid #ccc;
            border-radius: 5px;
            z-index: 10;
        }
        .info-container {
            top: 5px;
            left: 5px;
            text-align: left;
        }
        .time-container {
            top: 5px;
            right: 5px;
            text-align: right;
        }
        .weather-container {
            top: 5px;
            left: 250px;
            text-align: left;
        }
        .compass-container {
            width: 250px;
            height: 250px;
            margin: 10px auto;
            position: absolute;
            overflow: hidden;
            top: 130px;
            left: 750px;
            z-index: 20;
        }
        .compass-image {
            width: 50%;
            height: 50%;
            position: absolute;
            transform-origin: center;
            transition: transform 0.1s ease-out;
        }
        .map-container {
            width: 100%;
            height: 580px;
            margin: 5px auto;
            position: relative;
            z-index: 1;
        }
    </style>
</head>
<body>
    <div id="app">
        <div class="info-container">
            <p>纬度: {{ latitude }}</p>
            <p>经度: {{ longitude }}</p>
            <p>北斗卫星数量: {{ numSatellites }}</p>
            <p>海拔: {{ altitude }}</p>
            <p>导航航向: {{ headingRaw }}</p>
            <p>加速度 (X, Y, Z): {{ accelerationX }}, {{ accelerationY }}, {{ accelerationZ }} m/s²</p>
            <p>合加速度: {{ totalAcceleration.toFixed(2) }} m/s²</p>
            <p>航向角: {{ headingRaw }}°</p>
        </div>

        <div class="time-container">
            <p>北京时间: {{ beijingTime }}</p>
            <p>UTC时间: {{ utcTime }}</p>
        </div>

        <div class="weather-container">
            <p>北京怀柔区实时天气: {{ weather }}</p>
            <p>温度: {{ temperature }}℃</p>
            <p>风向: {{ windDirection }}</p>
            <p>风力: {{ windPower }}级</p>
            <p>湿度: {{ humidity }}%</p>
        </div>

        <div class="compass-container">
            <img id="compass" :style="{ transform: 'rotate(' + headingFiltered + 'deg)' }" src="/data/compass.png" alt="罗盘" class="compass-image">
        </div>

        <div class="map-container" id="map"></div>

        <div id="blinkingDot" class="blinking-dot" :style="{ display: isBlinking ? 'block' : 'none' }"></div>
    </div>

    <script src="/js/vue@2.js"></script>
    <script src="https://webapi.amap.com/maps?v=2.0&key=yourkey"></script>
    <script>
        new Vue({
            el: '#app',
            data: {youtkey
                latitude: '',
                longitude: '',
                numSatellites: '',
                altitude: '',
                trueNorthHeading: '',
                groundSpeed: '',
                groundSpeedKph: '',
                accelerationX: '',
                accelerationY: '',
                accelerationZ: '',
                totalAcceleration: 0,
                headingRaw: '',
                headingFiltered: '',
                beijingTime: '',
                utcTime: '',
                weather: '',
                temperature: '',
                windDirection: '',
                windPower: '',
                humidity: '',
                map: null,
                marker: null,
                isBlinking: false,
                lastUpdate: 0,
            },
            methods: {
                fetchData() {
                    fetch('/data/gps_imu_data.json')
                        .then(response => response.json())
                        .then(data => {
                            const utcTime = data.utc_time;
                            const utcDateTime = new Date('1970-01-01T' + utcTime.slice(0, 2) + ':' + utcTime.slice(2, 4) + ':' + utcTime.slice(4, 6) + 'Z');
                            const options = { hour: '2-digit', minute: '2-digit', second: '2-digit', timeZone: 'Asia/Shanghai' };
                            this.beijingTime = '2024.08.22 ' + new Intl.DateTimeFormat('zh-CN', options).format(utcDateTime);

                            this.utcTime = utcTime;
                            this.latitude = data.latitude.replace(/N|S/g, '').trim();
                            this.longitude = data.longitude.replace(/E|W/g, '').trim();
                            this.numSatellites = data.number_of_satellites;
                            this.altitude = data.altitude;
                            this.trueNorthHeading = data.true_north_heading;
                            this.groundSpeed = data.ground_speed_kn;
                            this.groundSpeedKph = data.ground_speed_kph;
                            this.accelerationX = data.x_accel_ms2;
                            this.accelerationY = data.y_accel_ms2;
                            this.accelerationZ = data.z_accel_ms2;
                            this.headingRaw = data.heading_raw_degrees;
                            this.headingFiltered = data.heading_filtered_degrees;

                            // 计算合加速度
                            this.totalAcceleration = Math.sqrt(
                                Math.pow(this.accelerationX, 2) +
                                Math.pow(this.accelerationY, 2) +
                                Math.pow(this.accelerationZ, 2)
                            );

                            // 更新地图位置
                            this.updateMap();
                        })
                        .catch(error => console.error('Error fetching data:', error));
                },
                fetchWeatherData() {
                    const cityCode = '110116'; 
                    const apiKey = 'yourkey';
                    const weatherUrl = `https://restapi.amap.com/v3/weather/weatherInfo?city=${cityCode}&extensions=base&key=${apiKey}`;

                    fetch(weatherUrl)
                        .then(response => response.json())
                        .then(data => {
                            const weatherInfo = data.lives[0];
                            this.weather = weatherInfo.weather;
                            this.temperature = weatherInfo.temperature;
                            this.windDirection = weatherInfo.winddirection;
                            this.windPower = weatherInfo.windpower;
                            this.humidity = weatherInfo.humidity;
                        })
                        .catch(error => console.error('Error fetching weather data:', error));
                },
                updateMap() {
                    if (this.map) {
                        if (this.marker) {
                            this.marker.setPosition([this.longitude, this.latitude]);
                            this.map.setCenter([this.longitude, this.latitude]);
                        } else {
                            this.marker = new AMap.Marker({
                                position: [this.longitude, this.latitude],
                                map: this.map,
                            });
                        }
                    } else {
                        this.map = new AMap.Map('map', {
                            zoom: 16,
                            center: [this.longitude, this.latitude],
                            viewMode: '2D',
                        });

                        this.marker = new AMap.Marker({
                            position: [this.longitude, this.latitude],
                            map: this.map,
                        });

                        AMap.plugin(['AMap.ToolBar', 'AMap.Scale', 'AMap.OverView', 'AMap.MapType', 'AMap.Layers'], () => {
                            this.map.addControl(new AMap.ToolBar());
                            this.map.addControl(new AMap.Scale());
                            this.map.addControl(new AMap.OverView({ isOpen: true }));
                            this.map.addControl(new AMap.MapType());

                            const trafficLayer = new AMap.TileLayer.Traffic({
                                zIndex: 10,
                                opacity: 0.8
                            });
                            this.map.add(trafficLayer);
                        });
                    }
                },
                updateBlinkingDot() {
                    fetch('status.txt')
                        .then(response => response.text())
                        .then(status => {
                            this.isBlinking = status.trim() === '1';
                        })
                        .catch(error => console.error('Error fetching status:', error));
                }
            },
            created() {
                this.fetchData();
                this.fetchWeatherData(); 
                this.updateBlinkingDot();
                setInterval(this.fetchData, 500); 
            }
        });
    </script>
</body>
</html>
