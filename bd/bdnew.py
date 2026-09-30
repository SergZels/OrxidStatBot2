import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from io import BytesIO
import numpy as np
import datetime
import os
import os.path
from peewee import *

from accounting import covered_months, format_amount, revenue_from_turnover

BASE_DIR = os.getenv("DATA_DIR", os.path.dirname(os.path.abspath(__file__)))
os.makedirs(BASE_DIR, exist_ok=True)
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
    ax.bar_label(rects1, padding=2, fmt='%g')  # це відступ від тексту до цифри
    ax.bar_label(rects2, padding=2, fmt='%g')
    fig.tight_layout()
    image = BytesIO()
    fig.savefig(image, format="png")
    plt.close(fig)
    return image.getvalue()


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
    def average_monthly(year, total=None):
        first = Stat.select(Stat.date).order_by(Stat.date).first()
        if first is None:
            return 0, 0
        months = covered_months(year, first.date, datetime.date.today())
        if total is None:
            turnover = (Stat.select(fn.SUM(Stat.cashAM + Stat.cashPM))
                        .where(Stat.date.year == year).scalar() or 0)
            total = revenue_from_turnover(turnover)
        return (round(total / months, 2) if months else 0), months

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

        st = "Статистика\n"
        chart = None
        cash_viruhka = []
        cash_vudatku = []
        datalabels = []
        monthcash = 0

        count = Stat.select().where((Stat.date.year == year) & (Stat.date.month == month)).count()
        if count > 0:
            for i in Stat.select().where((Stat.date.year == year) & (Stat.date.month == month)):
                turnover = int(i.cashAM) + int(i.cashPM)
                cash = revenue_from_turnover(turnover)
                monthcash = monthcash + cash
                st += (f"{i.date} виручка {format_amount(cash)} грн "
                       f"(оборот {format_amount(turnover)} грн: {i.cashAM} + {i.cashPM})\n")
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

            average, months = BotBDnew.average_monthly(year)
            st += f"\nОборот за місяць {format_amount(monthcash * 2)} грн\nВиручка за місяць {format_amount(monthcash)} грн\nВитрати за місяць {monthredet} грн\n\n" \
                  f"MAX виручка {format_amount(max(cash_viruhka))} грн.\nMIN виручка {format_amount(min(cash_viruhka))} грн.\n" \
                  f"Середня виручка за місяць у {year} році {format_amount(average)} грн (за {months} міс.)."
            chart = diagramBuilder(datalabels, cash_viruhka, cash_vudatku,
                                   month_interval=f"{month} місяць {format_amount(monthcash)} грн")

        return st, chart

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
                cash = revenue_from_turnover(int(i.cashAM) + int(i.cashPM))
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

            average, months = BotBDnew.average_monthly(year, monthcash)
            st += f"\nОборот за рік {format_amount(monthcash * 2)} грн\nВиручка за рік {format_amount(monthcash)} грн\nВитрати за рік {monthredet} грн\n\n" \
                  f"MAX виручка {format_amount(max(cash_viruhka))} грн.\nMIN виручка {format_amount(min(cash_viruhka))} грн.\n" \
                  f"Середня виручка за місяць {format_amount(average)} грн (за {months} міс.)"
        return st
