#! /usr/bin/python

import pygtk
pygtk.require('2.0')
import threading
import gobject
import gtk
import gtk.gdk
import gtk.glade

import glib
import datetime
import Queue
import requests
from apscheduler.scheduler import Scheduler

gobject.threads_init()

DIM_W = 200
DIM_H = 200

localdaytocron = {'lu': 'mon',
                  'ma': 'tue',
                  'me': 'wed',
                  'gi': 'thu',
                  've': 'fri',
                  'sa': 'sat',
                  'do': 'sun'}




programmi = {}
PROG_URL = "http://www.radiocicletta.it:80/programmi.json"
global_queue = Queue.Queue()
rawdata = requests.get(PROG_URL)
programmi = rawdata.json().get('programmi', [])
programmi = {str(x.get('blog_id', 'Nulla')): x for x in programmi}  # becco i programmi e li salvo per id


################ TEST ###############################

programmi['666'] = { u'blog_id': 666,
                          u'blog_url': u'/radiocicletta',
                          u'end': [u'me', 22, 36],
                          u'id': 6303981198376960,
                          u'logo': {u'descr': u'Logo generico di radiocicletta',
                                    u'title': u'Radiocicletta generic',
                                    u'url': u'http://i.imgur.com/Hj6qN.jpg'},
                          u'start': [u'lu', 22, 35],
                          u'stato': u'1',
                          u'title': u'Programma TESTA'}

#####################################################


def inserttask(**d):
    timerdate = {}
    timerato = False
    idp = d['id']
    value = programmi.get(idp, None)
    print "INSERITO! " +idp
    print value
    print "--"*30
    if value is not None and value.get('stato', '0') == '1':
        timerato = True
        timerdate['titolo'] = value['title']
        if value['end'][1] is 0:  # TODO: finiscono a mezzanotte per fix temporaneo li faccio finire alle 23:59:59
            timerdate['h'] = 23
            timerdate['m'] = 59
            timerdate['s'] = 59
        else:
            timerdate['h'] = value['end'][1]
            timerdate['m'] = value['end'][2]
            timerdate['s'] = 0
        r = requests.get(value['logo']['url'])
        timerdate['logo'] = r
    global_queue.put((timerato, timerdate))


class ScheduleThread(threading.Thread):
    def __init__(self):
        super(ScheduleThread, self).__init__()
        self.sched = Scheduler()

    def run(self):
        self.sched.start()

    def addschedule(self, **d):
        self.sched.add_cron_job(**d)


def makedialg(titolo):
    label = gtk.Label("Bona '%s', tempo scaduto\nlevati di culo." % titolo)
    dialog = gtk.Dialog("Tempo scaduto!",
                        None,
                        gtk.DIALOG_MODAL | gtk.DIALOG_DESTROY_WITH_PARENT,
                        (gtk.STOCK_CANCEL, gtk.RESPONSE_REJECT, gtk.STOCK_OK, gtk.RESPONSE_ACCEPT))
    dialog.vbox.pack_start(label)
    label.show()
    #checkbox = gtk.CheckButton("Useless checkbox")
    #dialog.action_area.pack_end(checkbox)
    #checkbox.show()
    response = dialog.run()
    dialog.destroy()


class Clock:

    def __init__(self):
        self.gladefile = "ui.glade"
        self.glade = gtk.Builder()
        self.glade.add_from_file(self.gladefile)
        self.glade.connect_signals(self)
        self.window = self.glade.get_object("window1")
        #self.window.connect("destroy", lambda w: gtk.main_quit())
        self.window.set_title("Clock")
        self.window.resize(DIM_W, DIM_H)
        self.orologio = self.glade.get_object("orologio")
        self.timer = self.glade.get_object("timer")
        self.ptitolo = self.glade.get_object("titolo")
        self.logo = self.glade.get_object("logo")
        self.window.show_all()
        self.timerato = False
        self.timerdate = {}
        self.icona = None  # ci metto l'icona del programma appena l'ho


    def update(self):
        dt = datetime.datetime.now()
        self.orologio.set_text('{:02d}:{:02d}:{:02d}'.format(dt.hour, dt.minute, dt.second))
        if not global_queue.empty():
            self.timerato, self.timerdate = global_queue.get()
            print "ESTRATTO! (%s, %s)" % (self.timerato, self.timerdate)
        if self.timerato:
            if self.icona is None:
                pbl = gtk.gdk.PixbufLoader()
                for chunk in self.timerdate['logo'].iter_content(chunk_size=1024):
                    if chunk: # filter out keep-alive new chunks
                        pbl.write(chunk)
                self.logo.set_from_pixbuf(pbl.get_pixbuf())
                pbl.close()
                self.icona = True
            datestr = "{:02d}:{:02d}:{:02d} {:02d}-{:02d}-{:02d}".format(self.timerdate['h'],
                                                                         self.timerdate['m'],
                                                                         self.timerdate['s'],
                                                                         dt.day,
                                                                         dt.month,
                                                                         dt.year)
            dn = datetime.datetime.strptime(datestr, '%H:%M:%S %d-%m-%Y')
            ddelta = (dn - dt)
            ts = ddelta.total_seconds()
            if ts <= 0:  # scaduto il timer, peso
                titolo = self.timerdate['titolo']
                self.timer.set_text("")
                self.ptitolo.set_text(titolo + " - FINITO!")
                self.timerato = False
                self.icona = None
                makedialg(titolo)
            else:
                self.timer.set_text(str(ddelta).split('.')[0])
                self.ptitolo.set_text(self.timerdate['titolo'])
        return True  # needed to keep the update method in the schedule

    def settimer(self, **d):
        idp = d['id']
        value = self.programmi.get(idp, None)
        if value is not None and value.get('stato', '0') == '1':
            self.timerato = True
            self.timerdate['titolo'] = value['title']
            if value['end'][1] is 0:  # TODO: finiscono a mezzanotte per fix temporaneo li faccio finire alle 23:59:59
                self.timerdate['h'] = 23
                self.timerdate['m'] = 59
                self.timerdate['s'] = 59
            else:
                self.timerdate['h'] = value['end'][1]
                self.timerdate['m'] = value['end'][2]
                self.timerdate['s'] = 0

    def unsettimer(self):
        pass


schedthread = ScheduleThread()

for k in programmi.keys():
    v = programmi[k]
    if v.get('stato', '0') == '1':
        print "messo "+ str(k)
        s_d, s_h, s_m = v['start']
        schedthread.addschedule(func=inserttask,
                                month="*",
                                day_of_week=localdaytocron[s_d],
                                hour=str(s_h),
                                minute=str(s_m),
                                kwargs={'id': str(k)})


def main():
    # Start the scheduler
    schedthread.run()
    gtk.main()

if __name__ == "__main__":
    clock = Clock()
    glib.timeout_add_seconds(1, clock.update)  # add to the main loop scheduled tasks
    print "OK"
    main()