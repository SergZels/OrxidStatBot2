import matplotlib.pyplot as plt
import numpy as np
import datetime
from statistics import mean
import os.path
from peewee import *

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
db_path = os.path.join(BASE_DIR, "botBD.db")
db = SqliteDatabase(db_path)


def diagramBuilder(datalabels, cash_viruhka, cash_vudatku, month_interval):
    x = np.arange(len(datalabels))  # the label locations
    width = 0.4  # the width of the bars
    fig, ax = plt.subplots()
    rects1 = ax.bar(x - width / 2, cash_viruhka, width, label='Виручка')
    rects2 = ax.bar(x + width / 2, cash_vudatku, width, label='Витрати')
    ax.set_ylabel('Виручка грн.')
    ax.set_title(f'Виручка за {month_interval}!')
    ax.set_xticks(x, datalabels)
    ax.legend()
    ax.bar_label(rects1, padding=2)  # це відступ від тексту до цифри
    ax.bar_label(rects2, padding=2)
    fig.tight_layout()
    plt.savefig("testplor.png")


class Stat(Model):
    cashAM = IntegerField(default=0)
    cashPM = IntegerField(default=0)
    date = DateField(default=datetime.date.today)
    time = DateField(default=datetime.datetime.now().strftime("%H:%M"))

    class Meta:
        database = db


class Credet(Model):
    cash = IntegerField(default=0)
    description = TextField()
    date = DateField(default=datetime.date.today)

    class Meta:
        database = db


class BotBDnew(Stat):

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        db.create_tables([Stat, Credet])

    @staticmethod
    def recAM(mes: str):
        now = datetime.datetime.now()
        count = Stat.select().where(
            (Stat.date.year == now.year) & (Stat.date.month == now.month) & (Stat.date.day == now.day)).count()
        if count == 1:
            ndays = Stat.get((Stat.date.year == now.year) & (Stat.date.month == now.month) & (Stat.date.day == now.day))
            ndays.cashAM = mes
            ndays.save()
        else:
            Stat.create(cashAM=mes)

    @staticmethod
    def recPM(mes: str):
        now = datetime.datetime.now()
        count = Stat.select().where(
            (Stat.date.year == now.year) & (Stat.date.month == now.month) & (Stat.date.day == now.day)).count()
        if count == 1:
            ndays = Stat.get((Stat.date.year == now.year) & (Stat.date.month == now.month) & (Stat.date.day == now.day))
            ndays.cashPM = mes
            ndays.save()
        else:
            Stat.create(cashPM=mes)

    @staticmethod
    def recCredet(cash: str, desc: str):
        Credet.create(cash=cash, description=desc)

    @staticmethod
    def statOfMonth(month, year) -> str:

        now = datetime.datetime.now()
        # now = now.replace(month=month, year=year)
        st = "Статистика\n"
        cash_viruhka = []
        cash_vudatku = []
        datalabels = []
        monthcash = 0

        count = Stat.select().where((Stat.date.year == year) & (Stat.date.month == month)).count()
        if count > 0:
            for i in Stat.select().where((Stat.date.year == year) & (Stat.date.month == month)):
                cash = int(i.cashAM) + int(i.cashPM)
                monthcash = monthcash + cash
                st += f"{i.date} було {cash} грн ({i.cashAM} {i.cashPM})\n"
                cash_viruhka.append(cash)
                datalabels.append(i.date.strftime("%d"))
                try:
                    srd = Credet.get(Credet.date == i.date)
                except:
                    cash_vudatku.append(0)
                else:
                    cash_vudatku.append(srd.cash)

            count2 = Credet.select().where((Credet.date.year == year) & (Credet.date.month == month)).count()
            monthredet = 0
            st += "\n"
            if count2 > 0:
                for i in Credet.select().where((Credet.date.year == year) & (Credet.date.month == month)):
                    monthredet += int(i.cash)
                    st += f"{i.date} витратили {i.cash} грн на {i.description}\n"

            st += f"\nВиручка за місяць {monthcash}\nВитрати за місяць {monthredet}\n\n" \
                  f"MAX виручка {max(cash_viruhka)} грн.\nMIN виручка {min(cash_viruhka)} грн.\n" \
                  f"Середня виручка {round(mean(cash_viruhka))} грн."
            diagramBuilder(datalabels, cash_viruhka, cash_vudatku, month_interval=f"{month} місяць {monthcash} грн")

        return st

    @staticmethod
    def statAllYear(year) -> str:

        now = datetime.datetime.now()
        now = now.replace(year=year)
        st = "Статистика за рік:\n"
        cash_viruhka = []
        cash_vudatku = []
        datalabels = []
        monthcash = 0

        count = Stat.select().where(Stat.date.year == year).count()
        if count > 0:
            for i in Stat.select().where(Stat.date.year == year):
                cash = int(i.cashAM) + int(i.cashPM)
                monthcash = monthcash + cash
                cash_viruhka.append(cash)
                datalabels.append(i.date.strftime("%d"))
                try:

                    srd = Credet.get(Credet.date == i.date)

                except:
                    cash_vudatku.append(0)
                else:
                    cash_vudatku.append(srd.cash)

            count2 = Credet.select().where(Credet.date.year == year).count()
            monthredet = 0

            if count2 > 0:
                for i in Credet.select().where(Credet.date.year == year):
                    monthredet += int(i.cash)

            st += f"\nВиручка за рік {monthcash}\nВитрати за рік {monthredet}\n\n" \
                  f"MAX виручка {max(cash_viruhka)} грн.\nMIN виручка {min(cash_viruhka)} грн.\n" \
                  f"Середня виручка {round(mean(cash_viruhka))} грн"
        return st
