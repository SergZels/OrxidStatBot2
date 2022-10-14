import sqlite3
import os.path
from statistics import mean
import matplotlib.pyplot as plt

class botBD:
	
	def __init__(self) -> None:
		BASE_DIR = os.path.dirname(os.path.abspath(__file__))
		db_path = os.path.join(BASE_DIR, "db_bot_tat.db")
		self.con = sqlite3.connect(db_path,check_same_thread=False)
		self.cursor = self.con.cursor()

	def close(self):
		self.con.close()

	def rec(self,mes:str):
		self.cursor.execute("INSERT INTO stat (cash) VALUES (?)",(mes,))
		self.con.commit()

	def stat(self):
		rows= self.cursor.execute("SELECT date,cash FROM stat WHERE strftime('%Y-%m','now')=strftime('%Y-%m',date) ORDER BY date").fetchall()
		st=""
		x=[]
		y=[]
		fig, ax = plt.subplots()

		for i in rows:
			st+=f"{i[0]} було {i[1]} грн.\n"
			dateOfcash=i[0]
			dateOf=dateOfcash[8:10]
			x.append(dateOf)
			y.append(i[1])
			ax.set_title(f'Виручка за місяць {dateOfcash[5:7]}')
			
		st+=f"\nMAX виручка {max(y)} грн.\nMIN виручка {min(y)} грн.\nСередня виручка {round(mean(y))} грн."
		ax.bar(x,y)
		ax.set_ylabel('грн')
		plt.savefig("testplor.png")
		
		return st
		