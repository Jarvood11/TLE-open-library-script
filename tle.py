from datetime import datetime, date
# Собственно клиент для space-track
# Набор операторов для управления запросами. Отсюда нам понадобится время
import spacetrack.operators as op
# Главный класс для работы с space-track
#from spacetrack import SpaceTrackClient
from   spacetrack  import   SpaceTrackClient
import shapefile

# Ключевой класс библиотеки pyorbital
from pyorbital.orbital import Orbital
# Имя пользователя и пароль сейчас опишем как константы
USERNAME = 'ewen12@yandex.ru'
#<YOUR SPACE-TRACK USERNAME>
PASSWORD = 'Wiu5YmhSkIMV1Wr3Y00x'
 #<YOUR SPACE-TRACK PASSWORD>
 
# Для примера реализуем всё в виде одной простой функции
# На вход она потребует идентификатор спутника, диапазон дат, имя пользователя и пароль. Опциональный флаг для последних данных tle
def get_spacetrack_tle (sat_id, start_date, end_date, username, password, latest=False):
    # Реализуем экземпляр класса SpaceTrackClient, инициализируя его именем пользователя и паролем
    st = SpaceTrackClient(identity=username, password=password)
    # Выполнение запроса для диапазона дат:
    if not latest:
        # Определяем диапазон дат через оператор библиотеки
        daterange = op.inclusive_range(start_date, end_date)
        # Собственно выполняем запрос через st.tle
        data = st.tle(norad_cat_id=sat_id, orderby='epoch desc', limit=1, format='tle', epoch = daterange)
    # Выполнение запроса для актуального состояния
    else:
        # Выполняем запрос через st.tle_latest
        data = st.tle_latest(norad_cat_id=sat_id, orderby='epoch desc', limit=1, format='tle')
 
    # Если данные недоступны
    if not data:
        return 0, 0
 
    # Иначе возвращаем две строки
    tle_1 = data[0:69]
    tle_2 = data[70:139]
    return tle_1, tle_2
	
tle_1, tle_2 = get_spacetrack_tle (39084, date(2016,5,11), date(2016,5,12), USERNAME, PASSWORD)
print (tle_1, tle_2)
print("New data:")
tle_1, tle_2 = get_spacetrack_tle (39084, None, None, USERNAME, PASSWORD, True)
print (tle_1, tle_2)



 
# Ещё одна простая функция, для демонстрации принципа.
# На вход она потребует две строки tle и время utc в формате datetime.datetime
def get_lat_lon_sgp (tle_1, tle_2, utc_time):
    # Инициализируем экземпляр класса Orbital двумя строками TLE
    orb = Orbital("N", line1=tle_1, line2=tle_2)
    # Вычисляем географические координаты функцией get_lonlatalt, её аргумент - время в UTC.
    lon, lat, alt = orb.get_lonlatalt(utc_time)
    return lon, lat

tle_1 = '1 25994U 99068A   16355.18348138  .00000089  00000-0  29698-4 0  9992'
tle_2 = '2 25994  98.2045  66.7824 0000703  69.9253 290.2059 14.57115924904601'
# Нас интересует текущий момент времени
utc_time = datetime.utcnow()
# Обращаемся к фукнции и выводим результат
print("Terra sputnik")
lon, lat = get_lat_lon_sgp (tle_1, tle_2, utc_time)
print (lon, lat)

# шаг в минутах для определения положения спутника, путь для результирующего файла
def create_orbital_track_shapefile_for_day (sat_id, track_day, step_minutes, output_shapefile):
    # Для начала получаем TLE    
    # Если запрошенная дата наступит в будущем, то запрашиваем самые последний набор TLE 
    if track_day > date.today():
        tle_1, tle_2 = get_spacetrack_tle (sat_id, None, None, USERNAME, PASSWORD, True)
    # Иначе на конкретный период, формируя запрос для указанной даты и дня после неё  + timedelta(days = 1)
    else:                   
        tle_1, tle_2 = get_spacetrack_tle (sat_id, track_day, track_day + timedelta(days = 1), USERNAME, PASSWORD, False)
 
    # Если не получилось добыть    
    if not tle_1 or not tle_2:
        print ('Impossible to retrieve TLE')        
        return
 
     # Создаём экземляр класса Orbital
    orb = Orbital("N", line1=tle_1, line2=tle_2)
 
    # Создаём экземпляр класса Writer для создания шейп-файла, указываем тип геометрии
    track_shape = shapefile.Writer(shapefile.POINT)
 
    # Добавляем поля - идентификатор, время, широту и долготу
    # N - целочисленный тип, C - строка, F - вещественное число
    # Для времени придётся использовать строку, т.к. нет поддержки формата "дата и время"
    track_shape.field('ID','N',40)
    track_shape.field('TIME','C',40)
    track_shape.field('LAT','F',40)
    track_shape.field('LON','F',40)
 
    # Объявляем счётчики, i для идентификаторов, minutes для времени
    i = 0
    minutes = 0
 
    # Простой способ пройти сутки - с заданным в минутах шагом дойти до 1440 минут.
    # Именно столько их в сутках!
    while minutes < 1440:
        # Расчитаем час, минуту, секунду (для текущего шага)
        utc_hour = int(minutes // 60)
        utc_minutes = int((minutes - (utc_hour*60)) // 1)
        utc_seconds = int(round((minutes - (utc_hour*60) - utc_minutes)*60))
 
        # Сформируем строку для атрибута
        utc_string = str(utc_hour) + '-' + str(utc_minutes) + '-' + str(utc_seconds)
        # И переменную с временем текущего шага в формате datetime
        utc_time = datetime(track_day.year,track_day.month,track_day.day,utc_hour,utc_minutes,utc_seconds)
 
        # Считаем положение спутника
        lon, lat, alt = orb.get_lonlatalt(utc_time)
 
        # Создаём в шейп-файле новый объект
        # Определеяем геометрию
        track_shape.point(lon,lat)
        # и атрибуты
        track_shape.record(i,utc_string,lat,lon)
 
        # Не забываем про счётчики
        i += 1
        minutes += step_minutes
 
    # Вне цикла нам осталось записать созданный шейп-файл на диск.
    # Т.к. мы знаем, что координаты положений ИСЗ были получены в WGS84
    # можно заодно создать файл .prj с нужным описанием
 
    try:
        # Создаем файл .prj с тем же именем, что и выходной .shp
        prj = open("%s.prj" % output_shapefile.replace('.shp',''), "w")
        # Создаем переменную с описанием EPSG:4326 (WGS84)
        wgs84_wkt = 'GEOGCS["WGS 84",DATUM["WGS_1984",SPHEROID["WGS 84",6378137,298.257223563]],PRIMEM["Greenwich",0],UNIT["degree",0.0174532925199433]]'
        # Записываем её в файл .prj        
        prj.write(wgs84_wkt)
        # И закрываем его
        prj.close()
        # Функцией save также сохраняем и сам шейп.
        track_shape.save(output_shapefile)
    except:
        # Вдруг нет прав на запись или вроде того...
        print ('Unable to save shapefile')
        return

		
create_orbital_track_shapefile_for_day(25994, date(2016,12,15), 5, '/home/silent/space/terra_15_12_2016_5min.shp')