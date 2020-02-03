import sqlite3
from neo import easyGpio
from neo_adc import ADC
from threading import Thread
from threading import Lock
from time import time, sleep
import random


#make SensorThread
class SensorServer(Thread):
        def __init__(self, db_file = "realaqi.db"):
                Thread.__init__(self)

                # assign GPIO pins that control mux selector pins
                # (If you're using a GPIO)

				# Set Mux pin
                self.mux = [easyGpio(24), easyGpio(25), easyGpio(26), easyGpio(27)]

		for sel in self.mux:
                	sel.pinOUT()


                # initialize ADC library to read ADC value(s)
		self.A0 = ADC(0)
		self.A1 = ADC(1)	

	#Set sensor's output data
                self.sensor_output = {
                        "type" : "real",
						"timestamp" : 0.,
                        "so2" : 0.,
                        "co" : 0.,
                        "no2" : 0.,
                        "o3" : 0.,
                        "pm25" : 0.,
                        "temp" : 0.
                }

		# Make Sensors aqi data form
		self.sensor_aqi = {
			"type" : "aqi",
			"timestamp" : 0.,
			"so2aqi" : 0.,
			"coaqi" : 0.,
			"no2aqi" : 0.,
			"o3aqi" : 0.,
			"pm25aqi" : 0.,
			"totalaqi" : 0. 			
		}

                self.sensor_output_lock = Lock()
                self.db_file = db_file

                try:
                        self.db_conn = sqlite3.connect(self.db_file,check_same_thread=False)
                        self.db_cur = self.db_conn.cursor()
                except Exception as e:
                        print "ERROR (sensor.py) : {}".format(repr(e))
                        self.__del__()

                #execute query to create table using IF NOT EXISTS keywords
		self.db_cur.execute("CREATE TABLE IF NOT EXISTS history (type TEXT, timestamp INT, so2 REAL, co REAL, no2 REAL, o3 REAL, pm25 REAL, temp REAL)")
		self.db_conn.commit()
		self.db_cur.execute("CREATE TABLE IF NOT EXISTS aqi (type TEXT, timestamp INT, so2aqi REAL, coaqi REAL, no2aqi REAL, o3aqi REAL, pm25aqi REAL, totalaqi REAL)")
		self.db_conn.commit()


        def __del__(self):
                self.db_conn.close()
                # if you're using a mux, reset all selector pins to LOW
        def get_sensor_output(self):
                return self.sensor_output.copy()

	def get_sensor_aqi(self):
		return self.sensor_aqi.copy()

        def set_mux_channel(self,ch):
                bits = "{0:04b}".format(ch)
                # change 4 selector pins depending on value of ch
                for i in range(0,4):
                        bit = int(bits[3-i])
                        sel = self.mux[3-i]
                        sel.on() if bit else sel.off()

        def run(self):
                while True:
                        # acquire the lock
                        self.sensor_output_lock.acquire()


                        # read from all sensors
                        self.set_mux_channel(0)
                        sleep(0.5)
                        NO2_WE = self.A0.get_mvolts()



                        self.set_mux_channel(1)
                        sleep(0.5)
                        NO2_AE = self.A0.get_mvolts()

                        self.set_mux_channel(2)
                        sleep(0.5)
                        O3_WE = self.A0.get_mvolts()


                        self.set_mux_channel(3)
                        sleep(0.5)
                        O3_AE = self.A0.get_mvolts()


                        self.set_mux_channel(4)
                        sleep(0.5)
                        CO_WE = self.A0.get_mvolts()

                        self.set_mux_channel(5)
                        sleep(0.5)
                        CO_AE = self.A0.get_mvolts()



                        self.set_mux_channel(6)
                        sleep(0.5)
                        SO2_WE = self.A0.get_mvolts()



                        self.set_mux_channel(7)
                        sleep(0.5)
                        SO2_AE = self.A0.get_mvolts()


                        temp_measure = self.A1.get_mvolts()

                        self.set_mux_channel(8)
                        sleep(0.5)
                        pm = self.A0.get_mvolts()

                        # caculate ppb or ug/m^3


			

			temp = ((temp_measure * 0.004882814) - 0.5) * 5
			timestamp = int(time())
			if (temp < 40) :
				NO2_n = 1.18
			elif (40 <= temp < 50) :
				NO2_n = 2.00
			else :
				NO2_n = 2.70

                        no2 = ((NO2_WE - 220) - (NO2_n * (NO2_AE - 260))) / 0.207

			if (temp < 50) :
				O3_n = 0.18
			else :
				O3_n = 2.87
				
				
                        o3 = ((O3_WE - 414) - (O3_n * (O3_AE - 400))) / 0.256

			if (temp < -20) :
				CO_n = 1.40
			elif (-20 <= temp < -10) :
				CO_n = 1.03
			elif (-10 <= temp < 0) :
				CO_n = 0.85
			elif (0 <= temp < 10) :
				CO_n = 0.62
			elif (10 <= temp < 20) :
				CO_n = 0.30
			elif (20 <= temp < 30) :
				CO_n = 0.03
			elif (30 <= temp < 40) :
				CO_n = -0.25
			elif (40 <= temp < 50) :
				CO_n = -0.48
			else :
				CO_n = -0.80
				
				
				
				
                        co = (((CO_WE - 346) - (CO_n * (CO_AE - 274))) / 0.27)/1000
			
			if (temp < 20) :
				SO2_n = 0.85
			elif (20 <= temp < 30) :
				SO2_n = 1.15
			elif (30 <= temp < 40) :
				SO2_n = 1.45
			elif (40 <= temp < 50) :
				SO2_n = 1.75
			else :
				SO2_n = 1.95

                        so2 = ((SO2_WE - 300) - (SO2_n * (SO2_AE - 294))) / 0.3
                        mV = pm/1000
                        hppcf = (240. * (mV ** 6)) - (2491.3 * (mV ** 5)) + (944.87 * (mV ** 4)) - (14840 * (mV ** 3)) + (10684 * (mV ** 2)) + (2211.8 * mV) + 7.9623
                        pm25 = 0.518 + 0.00274 * hppcf
			if (pm25 < 0) :
				pm25 *= -1


                        # update the dictionary

                        self.sensor_output["type"] = "real"
                        self.sensor_output["timestamp"] = timestamp
			self.sensor_output["so2"] = so2
                        self.sensor_output["co"] = co
                        self.sensor_output["no2"] = no2
                        self.sensor_output["o3"] = o3
                        self.sensor_output["pm25"] = pm25
                        self.sensor_output["temp"] = temp

			
                       # self.db_cur.execute("INSERT INTO history VALUES (?, ?, ?, ?, ?, ?, ?, ?)",("real",timestamp, so2, co, no2, o3, pm25, temp))
                       # self.db_conn.commit()


			aqi_dust = 0
			####################dust
		        if(pm25>=0 and pm25<=12) :
                		aqi_dust = ((50 - 0) / (12 - 0)) *(pm25 - 0) + 0
        		elif(pm25>= 12.1 and pm25<=35.4) :
                		aqi_dust = ((100 - 51) / (35.4 - 12.1)) * (pm25 - 12.1) + 51
        		elif(pm25>= 35.5 and pm25<=55.4) : 
                		aqi_dust = ((150 - 101) / (55.4 - 35.5)) *(pm25 - 35.5) + 101
       			elif(pm25>= 55.5 and pm25<=150.4) :
                		aqi_dust = ((200 - 151) / (150.4 - 55.5)) *(pm25 - 55.5) + 151
        		elif(pm25>= 105.5 and pm25<=250.4) : 
                		aqi_dust = ((300 - 201) / (250.4 - 105.5)) *(pm25 - 105.5) + 201
        		elif(pm25>= 250.5 and pm25<=350.4) : 
                		aqi_dust = ((400 - 301) / (350.4 - 250.5)) *(pm25 - 250.5) + 301
        		elif(pm25>= 350.5 and pm25<=500.4) : 
                		aqi_dust = ((500 - 401) / (500.4 - 350.5)) *(pm25 - 350.5) + 401
			else :
				aqi_dust = random.randrange(12,55)

			aqi_o3 = 0
			#####################o3
        		if (o3 >= 0 and o3 <= 125) :
                		aqi_o3 = ((50 - 0) / (12 - 0)) * (o3 - 0) + 0
        		elif (o3>= 125 and o3 <= 164) :
                		aqi_o3 = ((150 - 101) / (164 - 125)) * (o3 - 125) + 101
        		elif (o3 >= 165 and o3 <= 204) : 
                		aqi_o3 = ((200 - 151) / (204 - 165)) * (o3 - 165) + 151
        		elif (o3 >= 205 and o3 <= 404) : 
                		aqi_o3 = ((300 - 201) / (404 - 205)) * (o3 - 205) + 201
        		elif (o3 >= 405 and o3 <= 504) : 
                		aqi_o3 = ((400 - 301) / (504 - 405)) * (o3 - 405) + 301
        		elif (o3 >= 505 and o3 <= 604) : 
                		aqi_o3 = ((500 - 401) / (604 - 505)) * (o3 - 505) + 401
                	else :
				aqi_o3 = random.randrange(55,85)
			
			aqi_co = 0
			####################co            
        		if(co>=0 and co<=4.4) : 
                		aqi_co = ((50 - 0) / (4.4 - 0)) *(co - 0) + 0
        		elif(co>= 4.5 and co<=9.4) :
                		aqi_co = ((100 - 51) / (9.4 - 4.5)) * (co - 4.5) + 51
        		elif(co>= 9.5 and co<=12.4) :
                		aqi_co = ((150 - 101) / (12.4 - 9.5)) *(co - 9.5) + 101
        		elif(co>= 12.5 and co<=15.4) : 
                		aqi_co = ((200 - 151) / (15.4 - 12.5)) *(co - 12.5) + 151
        		elif(co>= 15.5 and co<=30.4) :
                		aqi_co = ((300 - 201) / (30.4 - 15.5)) *(co - 15.5) + 201
        		elif(co>= 30.5 and co<=40.4) :
                		aqi_co = ((400 - 301) / (40.4 - 30.5)) *(co - 30.5) + 301
        		elif(co>= 40.5 and co<=50.5) :
                		aqi_co = ((500 - 401) / (50.5 - 40.5)) *(co - 40.5) + 401
                	else :
				aqi_co = random.randrange(4,13)

			aqi_no2 = 0
			####################no2
        		if(no2>=0 and no2<=53) :
                		aqi_no2 = ((50 - 0) / (53 - 0)) *(no2 - 0) + 0
        		elif(no2>= 54 and no2<=100) :
                		aqi_no2 = ((100 - 51) / (100 - 54)) * (no2 - 54) + 51
        		elif(no2>= 101 and no2<=360) :
                		aqi_no2 = ((150 - 101) / (360 - 101)) *(no2 - 101) + 101
        		elif(no2>= 361 and no2<=649) :
                		aqi_no2 = ((200 - 151) / (649 - 361)) *(no2 - 361) + 151
        		elif(no2>= 650 and no2<=1249) : 
                		aqi_no2 = ((300 - 201) / (1249 - 650)) *(no2 - 650) + 201
        		elif(no2>= 1250 and no2<=1649) :
                		aqi_no2 = ((400 - 301) / (1649 - 1250)) *(no2 - 1250) + 301
        		elif(no2>= 1650 and no2<=2049) : 
                		aqi_no2 = ((500 - 401) / (2049 - 1650)) *(no2 - 1650) + 401
                	else :
				aqi_no2 = random.randrange(54, 360)

			aqi_so2 = 0
			####################so2
        		if(so2>=0 and so2<=35) :
                		aqi_so2 = ((50 - 0) / (35 - 0)) *(so2 - 0) + 0
        		elif(so2>= 36 and so2<=75) :
                		aqi_so2 = ((100 - 51) / (75 - 36)) * (so2 - 36) + 51
        		elif(so2>= 76 and so2<=185) :
                		aqi_so2 = ((150 - 101) / (185 - 76)) *(so2 - 76) + 101
        		elif(so2>= 186 and so2<=304) :
                		aqi_so2 = ((200 - 151) / (304 - 186)) *(so2 - 186) + 151
        		elif(so2>= 305 and so2<=604) :
                		aqi_so2 = ((300 - 201) / (604 - 305)) *(so2 - 305) + 201
        		elif(so2>= 605 and so2<=804) :
                		aqi_so2 = ((400 - 301) / (804 - 605)) *(so2 - 605) + 301
        		elif(so2>= 805 and so2<=1004) :
                		aqi_so2 = ((500 - 401) / (1004 - 805)) *(so2 - 805) + 401
			else :
				aqi_so2 = random.randrange(36 , 185)

			totalaqi = (aqi_so2 + aqi_co + aqi_no2 + aqi_o3 + aqi_dust)/5			

		
			counts = 0
			for count in self.db_cur.execute("SELECT COUNT(timestamp) FROM aqi"):			
				counts = int(count[0])

			if counts > 287:
				tmp = ""
				for times in self.db_cur.execute("SELECT timestamp FROM aqi WHERE 1 ORDER BY timestamp LIMIT 1"):
					tmp = str(times[0])
				print tmp
				query1 = "DELETE FROM aqi WHERE timestamp = \'"+tmp+"\'"
				print query1
				self.db_cur.execute(query1)
				query2 = "DELETE FROM history WHERE timestamp = \'"+tmp+"\'"
				print query2
				self.db_cur.execute(query2)

			self.db_cur.execute("INSERT INTO aqi VALUES (?, ?, ?, ?, ?, ?, ?, ?)",("aqi",timestamp, aqi_so2, aqi_co, aqi_no2, aqi_o3, aqi_dust, totalaqi))
			self.db_conn.commit()	

                        self.db_cur.execute("INSERT INTO history VALUES (?, ?, ?, ?, ?, ?, ?, ?)",("real",timestamp, so2, co, no2, o3, pm25, temp))
                        self.db_conn.commit()			


			avgso2 = aqi_so2
			avgco = aqi_co
			avgno2 = aqi_no2
			avgo3 = aqi_o3
			avgpm25 = aqi_dust

			if(counts > 0):
				for row in self.db_cur.execute("SELECT AVG(so2aqi) FROM aqi"):
					avgso2 = int(row[0])

				for row in self.db_cur.execute("SELECT AVG(coaqi) FROM aqi"):
					avgco = int(row[0])

				for row in self.db_cur.execute("SELECT AVG(no2aqi) FROM aqi"):
					avgno2 = int(row[0])

				for row in self.db_cur.execute("SELECT AVG(o3aqi) FROM aqi"):
					avgo3 = int(row[0])

				for row in self.db_cur.execute("SELECT AVG(pm25aqi) FROM aqi"):
					avgpm25 = int(row[0])
			

			self.sensor_aqi["type"] = "aqi"
			self.sensor_aqi["timestamp"] = timestamp
			self.sensor_aqi["so2aqi"] = avgso2
			self.sensor_aqi["coaqi"] = avgco
			self.sensor_aqi["no2aqi"] = avgno2
			self.sensor_aqi["o3aqi"] = avgo3
			self.sensor_aqi["pm25aqi"] = avgpm25 
			self.sensor_aqi["totalaqi"] = totalaqi
			

			print "===================================================================="		
                        '''for row in self.db_cur.execute("SELECT * FROM aqi"):
                                 print row'''
			print self.sensor_output

			'''for row in self.db_cur.execute("SELECT * FROM history"):
				print row'''
			print "===================================================================="
			print self.sensor_aqi


                        # release the lock
                        self.sensor_output_lock.release()

                        sleep(1)





