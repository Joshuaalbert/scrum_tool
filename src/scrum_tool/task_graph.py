import numpy as np
import pylab as plt
plt.style.use('ggplot')
import os
from datetime import datetime
import sqlite3 as sql
import pickle

class TaskGraph(object):
    def __init__(self, filename="project.db",new=False,allow_same_name=False):
        self.filename = os.path.abspath(filename)
        if new:
            try:
                os.unlink(filename)
            except:
                pass
        self.allow_same_name = allow_same_name
        self.setup()
        
        
    def setup(self):
        db = sql.connect(self.filename)
        c = db.cursor()
        c.execute(
                "CREATE TABLE IF NOT EXISTS workers\
                        ( worker_id INTEGER PRIMARY KEY,\
                        name TEXT)")
        c.execute(
                "CREATE TABLE IF NOT EXISTS tasks\
                        ( task_id INTEGER PRIMARY KEY,\
                        name TEXT, \
                        stat TEXT, \
                        workers TEXT, \
                        deps TEXT, \
                        length REAL, \
                        backlog_date TEXT, \
                        new_date TEXT, \
                        inprogress_date TEXT, \
                        finished_date TEXT, \
                        description TEXT, \
                        category TEXT)")

        c.execute(
                "CREATE TABLE IF NOT EXISTS hours\
                        (entry_id INTEGER PRIMARY KEY,\
                        task_id INTEGER, \
                        date TEXT, \
                        worker_id INTEGER, \
                        hours REAL, \
                        params TEXT)")

        c.execute(
                "CREATE TABLE IF NOT EXISTS sprints\
                        (sprint_id INTEGER PRIMARY KEY,\
                        name TEXT, \
                        tasks TEXT, \
                        start_date TEXT, \
                        end_date TEXT, \
                        scrum_master INTEGER)")

        db.commit()
        c.close()


    def to_datetime(self,datetime_str):
        try:
            return datetime.strptime(datetime_str,'%Y-%m-%d %H:%M:%S.%f')
        except:
            try:
                return datetime.strptime(datetime_str,'%Y-%m-%d')
            except:
                return datetime.strptime(datetime_str,'%Y-%m-%d %H:%M:%S')



    ###
    # Sprints

    @property
    def sprints(self):
        db = sql.connect(self.filename)
        c = db.cursor()
        c.execute('SELECT sprint_id,name from sprints')
        sprints = c.fetchall()
        c.close()
        if len(sprints) == 0:
            return []
        else:
            return ["{:03d}:{}".format(id,name) for id,name in sprints]

    def get_sprint_id_from_sprint(self,sprint):
        return int(sprint.split(":")[0].strip())

    def get_sprint_name_from_sprint(self,sprint):
        return sprint.split(":")[1].strip()

    def get_sprint_from_sprint_id(self,sprint_id):
        db = sql.connect(self.filename)
        c = db.cursor()
        c.execute('SELECT sprint_id,name from sprints where sprint_id=?',(sprint_id,))
        res = c.fetchall()
        c.close()
        if len(res) == 0:
            return None
        else:
            return "{:03d}:{}".format(res[0][0],res[0][1])

    def get_sprint_from_sprint_name(self,name):
        db = sql.connect(self.filename)
        c = db.cursor()
        c.execute('SELECT sprint_id,name from sprints where name=?',(name,))
        res = c.fetchall()
        c.close()
        if len(res) == 0:
            return None
        elif len(res) == 1:
            return "{:03d}:{}".format(res[0][0],res[0][1])
        else:
            raise ValueError("Invalid sprint {}".format(res))

    def resolve_sprint(self,sprint):
        if sprint in self.sprints:
            return sprint
        if isinstance(sprint,int):
            res = self.get_sprint_from_sprint_id(sprint)
        elif isinstance(sprint,str):
            res = self.get_sprint_from_sprint_name(sprint)
        if res is None:
            raise ValueError("Invalid sprint {}".format(sprint))
        return res


    @property
    def sprint_ids(self):
        return [self.get_sprint_id_from_sprint(t) for t in self.sprints]

    @property
    def sprint_names(self):
        return [self.get_sprint_name_from_sprint(t) for t in self.sprints]

    @property
    def next_sprint_id(self):
        db = sql.connect(self.filename)
        c = db.cursor()
        c.execute('SELECT max(sprint_id) from sprints')
        sprint_id = c.fetchall()
        c.close()
        if sprint_id[0][0] is None:
            return 1
        else:
            return sprint_id[0][0] + 1

    def add_sprint(self,name, tasks, start_date,end_date):

        tasks = [self.resolve_task(t) for t in tasks]
        task_ids = [self.get_task_id_from_task(t) for t in tasks]
        def _day(date):
            return datetime(date.year,date.month,date.day)
        start_date = _day(start_date)
        end_date = _day(end_date)

        db = sql.connect(self.filename)
        c = db.cursor()
        c.execute('insert into sprints(name, tasks, start_date, end_date) values(?,?,?,?)',(name,pickle.dumps(task_ids), start_date, end_date))
        db.commit()
        c.close()
        
        task_order = self.get_order_of_execution(tasks)
        stats = [self.get_task_stat(t) for t in task_order]
        for t,s in zip(task_order,stats):
            if s == 'backlog':
                self.update_task_stat(t,'new')



    def rm_sprint(self,sprint):
        sprint = self.resolve_sprint(sprint)
        sprint_id = self.get_sprint_id_from_sprint(sprint)
        db = sql.connect(self.filename)
        c = db.cursor()
        c.execute('DELETE FROM sprints WHERE sprint_id=?',(sprint_id,))
        db.commit()
        c.close()

    def update_sprint_end_date(self,sprint,date):
        sprint = self.resolve_sprint(sprint)
        sprint_id = self.get_sprint_id_from_sprint(sprint)
        db = sql.connect(self.filename)
        c = db.cursor()
        c.execute('UPDATE sprints set end_date=? \
                    WHERE sprint_id=?', (date, sprint_id))
        db.commit()
        c.close()

    def update_sprint_start_date(self,sprint,date):
        sprint = self.resolve_sprint(sprint)
        sprint_id = self.get_sprint_id_from_sprint(sprint)
        db = sql.connect(self.filename)
        c = db.cursor()
        c.execute('UPDATE sprints set start_date=? \
                    WHERE sprint_id=?', (date, sprint_id))
        db.commit()
        c.close()

    def get_all_sprints_with_task(self,task):
        task = self.resolve_task(task)
        task_id = self.get_task_id_from_task(task)
        db = sql.connect(self.filename)
        c = db.cursor()
        c.execute('SELECT sprint_id,tasks from sprints',(task_id,))
        res = c.fetchall()
        if len(res) == 0:
            return []
        has_task = []
        for r in res:
            if task_id in pickle.loads(r[1]):
                has_task.append(r[0])
        c.close()
        return [self.get_sprint_from_sprint_id(s) for s in has_task]
    
    def get_goal_tasks_from_sprint(self,sprint):
        sprint = self.resolve_sprint(sprint)
        sprint_id = self.get_sprint_id_from_sprint(sprint)
        db = sql.connect(self.filename)
        c = db.cursor()
        c.execute('SELECT tasks from sprints where sprint_id=?',(sprint_id,))
        res = c.fetchall()
        c.close()
        if len(res) == 0:
            return []
        return [self.get_task_from_task_id(t) for t in pickle.loads(res[0][0])]

    def get_tasks_from_sprint(self,sprint):
        goals = self.get_goal_tasks_from_sprint(sprint)
        return self.get_order_of_execution(goals)

    def get_workers_from_sprint(self,sprint):
        tasks = self.get_tasks_from_sprint(sprint)
        workers = []
        for t in tasks:
            workers.append(self.get_workers_from_task(t))
        return list(np.unique(workers))
        
    def get_expected_hours_for_sprint(self,sprint):
        tasks = self.get_tasks_from_sprint(sprint)
        return np.sum([self.get_task_length(t) for t in tasks])

    def get_expected_hours_of_remaining_tasks_for_sprint(self,sprint):
        tasks = self.get_remaining_tasks_from_sprint(sprint)
        return np.sum([self.get_task_length(t) for t in tasks])


    def get_completed_hours_for_sprint(self,sprint):
        tasks = self.get_tasks_from_sprint(sprint)
        return np.sum([self.get_hours_for_task(t) for t in tasks])

    def get_remaining_tasks_from_sprint(self,sprint):
        sprint = self.resolve_sprint(sprint)
        tasks = self.get_tasks_from_sprint(sprint)
        tasks_ = []
        for t in tasks:
            if self.get_task_stat(t) != 'finished':
                tasks_.append(t)
        return tasks_

    def is_sprint_finished(self,sprint,date=None):
        if date is None:
            date = datetime.today()
        sprint = self.resolve_sprint(sprint)
        start,end = self.get_dates_from_sprint(sprint)
        return (end.timestamp() - date.timestamp()) < 0

    def is_sprint_active(self,sprint,date=None):
        if date is None:
            date = datetime.today()
        sprint = self.resolve_sprint(sprint)
        start,end = self.get_dates_from_sprint(sprint)
        return (end.timestamp() - date.timestamp()) >= 0 and (start.timestamp() - date.timestamp()) <= 0

    def get_days_left_from_sprint(self,sprint):
        sprint = self.resolve_sprint(sprint)
        sprint_id = self.get_sprint_id_from_sprint(sprint)
        start,end = self.get_dates_from_sprint(sprint)
        def _day(date):
            return datetime(date.year,date.month,date.day)
        return (_day(end).timestamp() - _day(datetime.today()).timestamp())/86400. #you have the whole last day to finish

    def get_days_burned_from_sprint(self,sprint):
        sprint = self.resolve_sprint(sprint)
        sprint_id = self.get_sprint_id_from_sprint(sprint)
        start,end = self.get_dates_from_sprint(sprint)
        def _day(date):
            return datetime(date.year,date.month,date.day)
        return (_day(datetime.today()).timestamp()- _day(start).timestamp())/86400. + 1.#you have the whole last day to finish
        
    def get_dates_from_sprint(self,sprint):
        sprint = self.resolve_sprint(sprint)
        sprint_id = self.get_sprint_id_from_sprint(sprint)
        db = sql.connect(self.filename)
        c = db.cursor()
        c.execute('SELECT start_date,end_date from sprints where sprint_id=?',(sprint_id,))
        res = c.fetchall()
        c.close()
        if len(res) == 0:
            return None
        return (self.to_datetime(res[0][0]),  self.to_datetime(res[0][1]))

    def get_num_days_in_sprint(self,sprint):
        sprint = self.resolve_sprint(sprint)
        sprint_id = self.get_sprint_id_from_sprint(sprint)
        start,end = self.get_dates_from_sprint(sprint)
        return (end.timestamp() - start.timestamp())/86400. + 1.

    def suggest_next_task_for_sprint(self,sprint):
        sprint = self.resolve_sprint(sprint)
        tasks = self.get_goal_tasks_from_sprint(sprint)
        tasks = self.get_order_of_execution(tasks)
        for t in tasks:
            stat = self.get_task_stat(t)
            if stat != 'finished':
                return t
        return None

    def is_date_in_sprint(self,sprint,date):
        return self.is_sprint_active(sprint,date)
        
    def get_entries_in_sprint(self,sprint):
        sprint = self.resolve_sprint(sprint)
        tasks = self.get_tasks_from_sprint(sprint)
        entries = []
        for t in tasks:
            entries_ = self.get_hour_entries_for_task(t)
            for e in entries_:
                if self.is_date_in_sprint(sprint,self.to_datetime(e[2])):
                    entries.append(e)
        return entries

    def get_hours_burned_in_sprint(self,sprint):
        sprint = self.resolve_sprint(sprint)
        entries = self.get_entries_in_sprint(sprint)
        hours = 0.
        for e in entries:
            d = self.to_datetime(e[2]).timestamp()
            if d <= datetime.today().timestamp():
                hours += e[4]
        return hours

    def get_ideal_burn(self,sprint):
        sprint = self.resolve_sprint(sprint)
        length = self.get_expected_hours_for_sprint(sprint)
        days = self.get_num_days_in_sprint(sprint)
        return length/days

    def get_actual_burn(self,sprint):
        hours = self.get_hours_burned_in_sprint(sprint)
        days = self.get_days_burned_from_sprint(sprint)
        return hours/days

    def get_required_burn(self,sprint):
        sprint = self.resolve_sprint(sprint)
#        length = self.get_expected_hours_of_remaining_tasks_for_sprint(sprint)
        length = self.get_expected_hours_for_sprint(sprint)
        hours = self.get_hours_burned_in_sprint(sprint)
        days = self.get_days_left_from_sprint(sprint)
        return (length - hours)/days

    def get_projected_completion_of_sprint(self,sprint):
        sprint = self.resolve_sprint(sprint)
        length = self.get_expected_hours_for_sprint(sprint)
        actual_burn = self.get_actual_burn(sprint)
        start,end = self.get_dates_from_sprint(sprint)
        return start.timestamp() + 86400*length/actual_burn
        
    def get_daily_gain_in_sprint(self,sprint):
        sprint = self.resolve_sprint(sprint)
        start,end = self.get_dates_from_sprint(sprint)
        days = self.get_num_days_in_sprint(sprint)
        desired_end = end.timestamp() + 86400.#end of last day
        projected_end = self.get_projected_completion_of_sprint(sprint)
        if not np.isfinite(projected_end):
            return None
        return (desired_end - projected_end)/days/86400.

    def burndown_chart_for_sprint(self,sprint):

        def _day(date):
            return datetime(date.year,date.month,date.day)

        import matplotlib.dates as mdates
        fmt = mdates.DateFormatter('%Y-%m-%d')
        days = mdates.DayLocator()

        sprint = self.resolve_sprint(sprint)
        entries = self.get_entries_in_sprint(sprint)
        if len(entries) == 0:
            return False
        length = self.get_expected_hours_for_sprint(sprint)
        start,end = self.get_dates_from_sprint(sprint)
        
        time_array = np.arange(_day(start).timestamp(),_day(end).timestamp()+86400., 86400.)
        hours_left = np.ones(len(time_array))*length
        hours = np.zeros(len(time_array))
        for e in entries:
            d = self.to_datetime(e[2])
            idx = np.searchsorted(time_array,d.timestamp())
            hours_left[idx:] -= e[4]
            hours[idx] += e[4]
                
        ideal_burn = self.get_ideal_burn(sprint)
        actual_burn = self.get_actual_burn(sprint)
        projected_completion = start.timestamp() + 86400*length/actual_burn if actual_burn != 0. else np.nan
        required_burn = self.get_required_burn(sprint)

        dates = [datetime.fromtimestamp(t) for t in time_array]
        last = datetime.fromtimestamp(_day(end).timestamp()+86400.)
        x_max = datetime.fromtimestamp(min(max(projected_completion,_day(end).timestamp()+86400.), _day(end).timestamp()+5*86400.))
        days_left = []
        for i,d in enumerate(dates):
            if d.timestamp() > datetime.today().timestamp():
                days_left.append(d)
                hours_left[i:] = 0.

        fig,(ax,ax2) = plt.subplots(nrows=2,ncols=1,sharex=True,figsize=(12,12))
        ax.bar(dates, hours_left,align='edge',alpha=0.5)
        ax.plot([dates[0],last],[length, 0.],ls='--',lw=3,c='black',label='ideal burn {:.1f} hr/day'.format(ideal_burn))
#        ax.scatter([datetime.fromtimestamp(projected_completion)],[0.],s=100,c='blue',label='projected completion')
        ax.plot([dates[0],datetime.fromtimestamp(projected_completion)],[length,0.],ls='--',lw=3,c='blue',label='actual burn {:.1f} hr/day'.format(actual_burn))
        ax.vlines(datetime.today(),0.,length,color='green',lw=3,label='today')
        ax.legend()
        ax.set_title("Burndown for {}\nRunning {} to {}".format(self.get_sprint_name_from_sprint(sprint),
            dates[0].date(),dates[-1].date()))
        ax.xaxis.set_major_formatter(fmt)
        ax.xaxis.set_major_locator(days)
        ax.grid(True)
        ax.set_xlim(dates[0],x_max)
        ax.set_ylabel('hours')

        ax2.bar(dates, hours,align='edge',alpha=0.5)
        if len(days_left) > 0:
            ax2.bar(days_left, required_burn*np.ones(len(days_left)),alpha=0.5,align='edge',label='goal {:.1f} hr/day'.format(required_burn))
        ax2.vlines(datetime.today(),0.,length,color='green',lw=3)
        ax2.set_title("Hours per day\nDaily hourly gain {:.1f}".format(self.get_daily_gain_in_sprint(sprint)))
        ax2.xaxis.set_major_formatter(fmt)
        ax2.xaxis.set_major_locator(days)
        ax2.grid(True)
        ax2.set_xlim(dates[0],x_max)
        ax2.set_ylabel('hours')
        ax2.set_xlabel('date')
        if len(days_left) > 0:
            ax2.legend()

        fig.autofmt_xdate()
        plt.tight_layout()
        plt.show()
        return True


        
        
        
    ###
    # Tasks    

    @property
    def tasks(self):
        db = sql.connect(self.filename)
        c = db.cursor()
        c.execute('SELECT task_id,name from tasks')
        tasks = c.fetchall()
        c.close()
        if len(tasks) == 0:
            return []
        else:
            return ["{:03d}:{}".format(id,name) for id,name in tasks]
    
    def get_task_id_from_task(self,task):
        return int(task.split(":")[0].strip())

    def get_task_name_from_task(self,task):
        return task.split(":")[1].strip()

    def resolve_task(self,task):
        if task in self.tasks:
            return task
        if isinstance(task,int):
            res = self.get_task_from_task_id(task)
        elif isinstance(task,str):
            res = self.get_task_from_task_name(task)
        if res is None:
            raise ValueError("Invalid task {}".format(task))
        return res

    @property
    def task_ids(self):
        return [self.get_task_id_from_task(t) for t in self.tasks]

    @property
    def task_names(self):
        return [self.get_task_name_from_task(t) for t in self.tasks]

    def get_task_from_task_id(self,task_id):
        db = sql.connect(self.filename)
        c = db.cursor()
        c.execute('SELECT task_id,name from tasks where task_id=?',(task_id,))
        res = c.fetchall()
        c.close()
        if len(res) == 0:
            return None
        else:
            return "{:03d}:{}".format(res[0][0],res[0][1])

    def get_task_from_task_name(self,name):
        db = sql.connect(self.filename)
        c = db.cursor()
        c.execute('SELECT task_id,name from tasks where name=?',(name,))
        res = c.fetchall()
        c.close()
        if len(res) == 0:
            return None
        elif len(res) == 1:
            return "{:03d}:{}".format(res[0][0],res[0][1])
        else:
            raise ValueError("Duplicate task {}".format(res))

    def get_workers_from_task(self,task):
        task = self.resolve_task(task)
        task_id = self.get_task_id_from_task(task)
        db = sql.connect(self.filename)
        c = db.cursor()
        c.execute('SELECT workers from tasks WHERE task_id=?',(task_id,))
        workers = c.fetchall()
        c.close()        
        if len(workers) == 0:
            return []
        elif len(workers) == 1:
            return [self.get_worker_from_worker_id(w) for w in pickle.loads(workers[0][0])]
        else:
            raise ValueError("Duplicate task {}".format(task))

    def get_deps_from_task(self,task):
        task = self.resolve_task(task)
        task_id = self.get_task_id_from_task(task)
        db = sql.connect(self.filename)
        c = db.cursor()
        c.execute('SELECT deps from tasks WHERE task_id=?',(task_id,))
        res = c.fetchall()
        c.close()        
        if len(res) == 0:
            return []
        elif len(res) == 1:
            return [self.get_task_from_task_id(t) for t in pickle.loads(res[0][0])]
        else:
            raise ValueError("Duplicate task {}".format(task))

    def get_description_from_task(self,task):
        task = self.resolve_task(task)
        task_id = self.get_task_id_from_task(task)
        db = sql.connect(self.filename)
        c = db.cursor()
        c.execute('SELECT description from tasks WHERE task_id=?',(task_id,))
        res = c.fetchall()
        c.close()        
        if len(res) == 0:
            return []
        elif len(res) == 1:
            return res[0][0]
        else:
            raise ValueError("Duplicate task {}".format(task))


    def add_task(self,name, length, workers, deps=None, date=None, description=None):
        if not self.allow_same_name:
            if name in self.task_names:
                raise ValueError("Task {} already exists".format(name))
        if date is None:
            date = datetime.today()

        if description is None:
            description = ''

        if not isinstance(workers,(tuple,list)):
            workers = [workers]
        
        workers = [self.resolve_worker(w) for w in workers]
        
        workers = [self.get_worker_id_from_worker(w) for w in workers]

        if deps is None:
            deps = []

        if not isinstance(deps,(tuple,list)):
            deps = [deps]

        deps = [self.resolve_task(t) for t in deps]
        deps = [self.get_task_id_from_task(t) for t in deps]

        db = sql.connect(self.filename)
        c = db.cursor()
        c.execute('INSERT INTO tasks(name, length, workers, deps, stat, backlog_date, description) VALUES(?,?,?,?,?,?,?)',
                (name, float(length), pickle.dumps(workers), pickle.dumps(deps), 'backlog', date, description))
        db.commit()
        c.close()

    def rm_task(self,task):
        task = self.resolve_task(task)
        
        tasks = self.tasks
        for t in tasks:
            deps = self.get_deps_from_task(t)
            deps_ = []
            for d in deps:
                if d != task:
                    deps_.append(d)
            self.update_task_deps(t,deps_)

        task_id = self.get_task_id_from_task(task)
        db = sql.connect(self.filename)
        c = db.cursor()
        c.execute('DELETE from tasks where task_id=?',(task_id,))
        db.commit()
        c.close()



    def get_task_length(self,task):
        task = self.resolve_task(task)
        task_id = self.get_task_id_from_task(task)
        db = sql.connect(self.filename)
        c = db.cursor()
        c.execute('SELECT length from tasks where task_id=?',(task_id,))
        res = c.fetchall()
        c.close()
        if len(res) == 0:
            return None
        else:
            return res[0][0]


    def get_task_stat(self,task):
        task = self.resolve_task(task)
        task_id = self.get_task_id_from_task(task)
        db = sql.connect(self.filename)
        c = db.cursor()
        c.execute('SELECT stat from tasks where task_id=?',(task_id,))
        res = c.fetchall()
        c.close()
        if len(res) == 0:
            return None
        else:
            return res[0][0]


    def update_task_workers(self,task, workers):
        task = self.resolve_task(task)
        task_id = self.get_task_id_from_task(task)
        workers = [self.resolve_worker(w) for w in workers]
        workers = [self.get_worker_id_from_worker(w) for w in workers]
        db = sql.connect(self.filename)
        c = db.cursor()
        c.execute('UPDATE tasks set workers=? \
                    WHERE task_id=?', (pickle.dumps(workers),task_id))
        db.commit()
        c.close()


    def update_task_deps(self,task,deps):
        task = self.resolve_task(task)
        task_id = self.get_task_id_from_task(task)
        deps = [self.resolve_task(t) for t in deps]
        deps_ = []
        for d in deps:
            if d != task:
                deps_.append(d)
        deps = [self.get_task_id_from_task(t) for t in deps_]
        db = sql.connect(self.filename)
        c = db.cursor()
        c.execute('UPDATE tasks set deps=? \
                    WHERE task_id=?', (pickle.dumps(deps),task_id))
        db.commit()
        c.close()

    def update_task_length(self,task,length):
        task = self.resolve_task(task)
        task_id = self.get_task_id_from_task(task)
        db = sql.connect(self.filename)
        c = db.cursor()
        c.execute('UPDATE tasks set length=? \
                    WHERE task_id=?', (length,task_id))
        db.commit()
        c.close()

    def update_task_description(self,task,description):
        task = self.resolve_task(task)
        task_id = self.get_task_id_from_task(task)
        db = sql.connect(self.filename)
        c = db.cursor()
        c.execute('UPDATE tasks set description=? \
                    WHERE task_id=?', (description,task_id))
        db.commit()
        c.close()

    def update_task_stat(self,task,stat,date=None):
        task = self.resolve_task(task)
        task_id = self.get_task_id_from_task(task)

        if date is None:
            date = datetime.today()

        if stat  == 'backlog':
            db = sql.connect(self.filename)
            c = db.cursor()
            c.execute('UPDATE tasks set stat=?, backlog_date=? \
                        WHERE task_id=?', (stat,date,task_id))
            db.commit()
            c.close()

        if stat  == 'new':
            db = sql.connect(self.filename)
            c = db.cursor()
            c.execute('UPDATE tasks set stat=?, new_date=? \
                        WHERE task_id=?', (stat,date,task_id))
            db.commit()
            c.close()

        if stat  == 'inprogress':
            db = sql.connect(self.filename)
            c = db.cursor()
            c.execute('UPDATE tasks set stat=?, inprogress_date=? \
                        WHERE task_id=?', (stat,date,task_id))
            db.commit()
            c.close()
        if stat  == 'finished':
            db = sql.connect(self.filename)
            c = db.cursor()
            c.execute('UPDATE tasks set stat=?, finished_date=? \
                        WHERE task_id=?', (stat,date,task_id))
            db.commit()
            c.close()

    def get_task_dsk(self):
        tasks = self.tasks
        task_ids = [self.get_task_id_from_task(t) for t in tasks]
        dsk = {}
        for task_id,task in zip(task_ids,tasks):
            db = sql.connect(self.filename)
            c = db.cursor()
            c.execute('SELECT deps FROM tasks WHERE task_id=?',(task_id, ))
            res = c.fetchall()
            c.close()
            if len(res) == 0:
                dsk[task] = []
            else:
                dsk[task] = [self.get_task_from_task_id(t) for t in pickle.loads(res[0][0])]
        return dsk

    def get_order_of_execution(self, tasks):
        from dask.callbacks import Callback
        from dask import get

        if not isinstance(tasks,(tuple,list)):
            tasks = [tasks]

        tasks = [self.resolve_task(t) for t in tasks]

        task_dsk = self.get_task_dsk()

        def _op(*args):
            return args
        dsk = {}
        for key in task_dsk.keys():
            if len(task_dsk[key]) == 0:
                dsk[key] = (_op,)
            else:
                dsk[key] = (_op,task_dsk[key])
                
        order = []
        class PrintKeys(Callback):
            def __init__(self):
                pass
            def _start(self,dsk):
                pass
            def _pretask(self, key, dask, state):
                pass
            def _posttask(self,key,result,dsk,state,id):
                order.append("{}".format(repr(key)[1:-1]))
                assert order[-1] in dsk.keys(), "Formatting error occured"
            def _finish(self,dsk,state,errored):
                pass
        with PrintKeys():
            get(dsk,tasks)
        return order


    ###
    # Workers
        
    @property
    def workers(self):
        db = sql.connect(self.filename)
        c = db.cursor()
        c.execute('SELECT worker_id,name from workers')
        workers = c.fetchall()
        c.close()
        if len(workers) == 0:
            return []
        else:
            return ["{:03d}:{}".format(id,name) for id,name in workers]

    def get_worker_id_from_worker(self,worker):
        return int(worker.split(":")[0].strip())

    def get_worker_name_from_worker(self,worker):
        return worker.split(":")[1].strip()

    def get_worker_from_worker_id(self,worker_id):
        db = sql.connect(self.filename)
        c = db.cursor()
        c.execute('SELECT worker_id,name from workers where worker_id=?',(worker_id,))
        res = c.fetchall()
        c.close()
        if len(res) == 0:
            return None
        else:
            return "{:03d}:{}".format(res[0][0],res[0][1])

    def get_worker_from_worker_name(self,name):
        db = sql.connect(self.filename)
        c = db.cursor()
        c.execute('SELECT worker_id,name from workers where name=?',(name,))
        res = c.fetchall()
        c.close()
        if len(res) == 0:
            return None
        elif len(res) == 1:
            return "{:03d}:{}".format(res[0][0],res[0][1])
        else:
            raise ValueError("Invalid worker {}".format(res))

    def resolve_worker(self,worker):
        if worker in self.workers:
            return worker
        if isinstance(worker,int):
            res = self.get_worker_from_worker_id(worker)
        elif isinstance(worker,str):
            res = self.get_worker_from_worker_name(worker)
        if res is None:
            raise ValueError("Invalid worker {}".format(worker))
        return res


    @property
    def worker_ids(self):
        return [self.get_worker_id_from_worker(t) for t in self.workers]

    @property
    def worker_names(self):
        return [self.get_worker_name_from_worker(t) for t in self.workers]

    @property
    def next_worker_id(self):
        db = sql.connect(self.filename)
        c = db.cursor()
        c.execute('SELECT max(worker_id) from workers')
        worker_id = c.fetchall()
        c.close()
        if worker_id[0][0] is None:
            return 1
        else:
            return worker_id[0][0] + 1

    def add_worker(self,name):
        db = sql.connect(self.filename)
        c = db.cursor()
        c.execute('insert into workers(name) values(?)',(name,))
        db.commit()
        c.close()


    def rm_worker(self,worker):
        worker = self.resolve_worker(worker)
        worker_id = self.get_worker_id_from_worker(worker)
        db = sql.connect(self.filename)
        c = db.cursor()
        c.execute('DELETE FROM workers WHERE worker_id=?',(worker_id,))
        db.commit()
        c.close()

    def get_tasks_from_worker(self,worker):
        worker = self.resolve_worker(worker)
        worker_id = self.get_worker_id_from_worker(worker)
        db = sql.connect(self.filename)
        c = db.cursor()
        c.execute('SELECT task_id,workers from tasks')
        res = c.fetchall()
        c.close()  
        if len(res) == 0:
            return []
        has_worker = []
        for r in res:
            if worker_id in pickle.loads(r[1]):
                has_worker.append(r[0])
        return [self.get_task_from_task_id(h) for h in has_worker]

    def get_sprints_from_worker(self,worker):
        worker = self.resolve_worker(worker)
        worker_id = self.get_worker_id_from_worker(worker)
        db = sql.connect(self.filename)
        c = db.cursor()
        c.execute('SELECT sprint_id from sprints')
        res = c.fetchall()
        c.close()  
        if len(res) == 0:
            return []
        has_worker = []
        for r in res:
            if worker_id in self.get_workers_from_sprint(r[0]):
                has_worker.append(r[0])
        return [self.get_sprint_from_sprint_id(h) for h in has_worker]

    def get_expected_hours_for_worker(self,worker):
        sprints = self.get_sprints_from_worker(worker)
        return np.sum([self.get_expected_hours_for_sprint(s) for s in sprints])

    ###
    # Hours

    def add_hours(self, task, date, worker, hours):
        '''
        Data should be datetime object
        '''
        task = self.resolve_task(task)
        worker = self.resolve_worker(worker)

        task_id = self.get_task_id_from_task(task)
        worker_id = self.get_worker_id_from_worker(worker)
        
        db = sql.connect(self.filename)
        c = db.cursor()
        c.execute('INSERT INTO hours(task_id, date, worker_id, hours) VALUES(?,?,?,?)',(task_id, date.date(), worker_id, hours))
        db.commit()
        c.close()
        stat = self.get_task_stat(task)
        if stat != 'inprogress':
            self.update_task_stat(task,'inprogress',date)

    def rm_hours(self, task, date, worker):
        task = self.resolve_task(task)
        worker = self.resolve_worker(worker)

        task_id = self.get_task_id_from_task(task)
        worker_id = self.get_worker_id_from_worker(worker)

        db = sql.connect(self.filename)
        c = db.cursor()
        c.execute('DELETE FROM hours WHERE task_id=? AND date=? AND worker_id=?',(task_id, date.date(), worker_id))
        db.commit()
        c.close()

    def get_hour_entries_for_task(self,task):
        task = self.resolve_task(task)
        task_id = self.get_task_id_from_task(task)
        db = sql.connect(self.filename)
        c = db.cursor()
#        c.execute('SELECT date,worker_id,hours FROM hours WHERE task_id=?',(task_id, ))
        c.execute('SELECT * FROM hours WHERE task_id=?',(task_id, ))
        res = c.fetchall()
        c.close()
        return res

    def get_hours_for_task(self,task):
        task = self.resolve_task(task)
        task_id = self.get_task_id_from_task(task)
        db = sql.connect(self.filename)
        c = db.cursor()
        c.execute('SELECT hours FROM hours WHERE task_id=?',(task_id, ))
        res = c.fetchall()
        c.close()
        return np.sum(res)

    def get_hours_for_worker(self,worker):
        worker = self.resolve_worker(worker)
        worker_id = self.get_worker_id_from_worker(worker)
        db = sql.connect(self.filename)
        c = db.cursor()
        c.execute('SELECT hours FROM hours WHERE worker_id=?',(worker_id, ))
        res = c.fetchall()
        c.close()
        return np.sum(res)


    def get_entries_for_worker(self,worker):
        worker = self.resolve_worker(worker)
        worker_id = self.get_worker_id_from_worker(worker)
        db = sql.connect(self.filename)
        c = db.cursor()
        c.execute('SELECT date,hours,task_id FROM hours WHERE worker_id=?',(worker_id, ))
        res = c.fetchall()
        c.close()
        return [[r[0], r[1], self.get_task_from_task_id(r[2])] for r in res]
    
def test():
    tg = TaskGraph(filename='test.db',new=True)
    tg.add_worker('abc')
    tg.add_worker('abcd')
    tg.add_task('a',1.,1,[])
    tg.add_task('b',1.,[1,2],'a')
    tg.add_task('c',1.,2,['a'])
    tg.add_hours('a',datetime.today(),1,1.)
    tg.update_task_workers('a',[1,2])
    tg.add_sprint('sprint A', [1,2],datetime.fromtimestamp(datetime.today().timestamp() - 86400.*2),datetime.fromtimestamp(datetime.today().timestamp() + 86400.*2))
    print(tg.workers)
    print(tg.get_order_of_execution('c'))
    print(tg.get_workers_from_task('a'))
    print(tg.get_task_stat('a'))
    print(tg.next_sprint_id)
    tg.burndown_chart_for_sprint(1)


if __name__ == '__main__':
    test()

