import numpy as np
import npyscreen
from datetime import datetime
from scrum_tool.task_graph import TaskGraph
import os

class SwitchFormMultiLineAction(npyscreen.MultiLineAction):
    def __init__(self, *args, **keywords):
        super(SwitchFormMultiLineAction, self).__init__(*args, **keywords)
        self.switch_dict = keywords.get('switch_dict',{})

    def actionHighlighted(self, act_on_this, keypress):
        for k in self.switch_dict:
            if k == act_on_this:
                self.parent.parentApp.switchForm(self.switch_dict[k])
                break

###
# Main form

class RecordListDisplay(npyscreen.FormMutt):
    MAIN_WIDGET_CLASS = SwitchFormMultiLineAction
    COMMAND_WIDGET_CLASS = npyscreen.TitleFilename
    COMMAND_WIDGET_NAME = 'Load db:'

    def beforeEditing(self):
        self.wMain.values = ["Manage workers","Manage tasks", "Manage sprints"]
        self.wMain.switch_dict = {"Manage workers":"MANAGEWORKERS","Manage tasks":"MANAGETASKS", "Manage sprints":"MANAGESPRINTS"}
        self.wMain.display()
        self.wCommand.value = 'database.db'
        self.add_handlers({
            "?": self.when_help,
            "L": self.when_load,
            "C": self.when_new
        })
    def when_load(self, *args, **kwargs):
        self.wCommand.value = os.path.abspath(self.wCommand.value)
        self.wCommand.update()
        self.parentApp.taskGraph.filename = self.wCommand.value
        self.parentApp.taskGraph.setup()
        
    def when_new(self, *args, **kwargs):
        self.wCommand.value = os.path.abspath(self.wCommand.value)
        self.wCommand.update()
        
        if os.path.exists(self.wCommand.value):
            if npyscreen.notify_yes_no("{} already exists, overwrite?".format(self.wCommand.value)):
                os.unlink(self.wCommand.value)
                self.parentApp.taskGraph.filename = self.wCommand.value
                self.parentApp.taskGraph.setup()
        else:
            self.parentApp.taskGraph.filename = self.wCommand.value
            self.parentApp.taskGraph.setup()


    def when_help(self, *args, **keywords):
        npyscreen.notify_confirm(
                "L Load the selected database file (database.db is default)\n" + \
                "C Creates the file if it doesn't already exist\n" + \
                "== General keybindings ==\n" + \
                "q Return to previous screen\n" + \
                "TAB and arrow keys to move around\n" + \
                "Ctrl+c Exit program\n" + \
                "== Further info ==\n" + \
                "All modifcations are auto-saved")


###
# Manage sprints

class SprintMultiLineAction(npyscreen.MultiLineAction):
    def __init__(self, *args, **keywords):
        super(SprintMultiLineAction, self).__init__(*args, **keywords)

    def actionHighlighted(self, act_on_this, keypress):
        self.parent.parentApp.getForm('EDITSPRINT').value = act_on_this#sprint
        self.parent.parentApp.switchForm('EDITSPRINT')
        
class ManageSprints(npyscreen.ActionForm):
    def create(self):
        self.wgAdd = self.add(SwitchFormMultiLineAction,values = ['Create new sprint'],max_height=2,switch_dict={'Create new sprint':'ADDSPRINT'},scroll_exit=True)
        self.wgTitle1 = self.add(npyscreen.TitleText,name='Manage sprints',editable=False)
        self.wgSprints   = self.add(SprintMultiLineAction, values = self.parentApp.taskGraph.sprints, max_height=5,scroll_exit=True)
        self.add_handlers({
            "?": self.when_help,
        })
        self.add_handlers({
            "q": self.when_previous,
            })

    def when_previous(self,*args,**kwargs):
        self.parentApp.switchFormPrevious()

    def when_help(self, *args, **keywords):
        npyscreen.notify_confirm(
                "== General keybindings ==\n" + \
                "q Return to previous screen\n" + \
                "TAB and arrow keys to move around\n" + \
                "Ctrl+c Exit program\n" + \
                "== Further info ==\n" + \
                "All modifcations are auto-saved")
        
    def update(self):
        self.wgSprints.values = self.parentApp.taskGraph.sprints
        self.wgSprints.update()

    def beforeEditing(self):
        self.update()

    def on_ok(self):
        self.update()
        self.parentApp.switchFormPrevious()

    def on_cancel(self):
        self.parentApp.switchFormPrevious()

class AddSprint(npyscreen.ActionForm):
    def create(self):
        self.wgId   = self.add(npyscreen.TitleText, name = "Sprint id:", 
                editable=False)
        self.wgName   = self.add(npyscreen.TitleText, name = "Sprint Name:")
        self.wgStart = self.add(npyscreen.TitleDateCombo, value=datetime.today(), name = "Start Date:")
        self.wgEnd = self.add(npyscreen.TitleDateCombo, value=datetime.today(), name = "End Date:")
        self.wgTasks = self.add(npyscreen.TitleMultiSelect, max_height = 5, value = [], name="Goal task(s):", scroll_exit=True)
        self.name = "New Sprint"
        self.add_handlers({
            "q": self.when_previous,
            "?": self.when_help
            })

    def when_help(self, *args, **kwargs):
        npyscreen.notify_confirm("== Sprints ==\n" + \
                "Adding tasks to a sprint changes their stats from backlog to new if not already done. It is possible for the task to appear in multiple sprints, but this may confuse the burndown calculations. Ideally, try to choose goal tasks that depend on common dependences. Make sure you fill in a valid name, and start and end dates of the sprint. We assume each day allows 8 working hours. If a worker performs more or less than this, it will reflect in their avg. efficiency. When selecting tasks for a sprint, simply select the end-point (goal) tasks and their dependencies will automatically be add in the suggested optimal completion order.\n" + \
                "== General keybindings ==\n" + \
                "q Return to previous screen\n" + \
                "TAB and arrow keys to move around\n" + \
                "Ctrl+c Exit program\n" + \
                "== Further info ==\n" + \
                "All modifcations are auto-saved")

    def when_previous(self,*args,**kwargs):
        self.parentApp.switchFormPrevious()

    def update(self):
        self.wgStart.value = datetime.today()
        self.wgEnd.value = datetime.today()
        self.wgName.value = ''
        self.wgTasks.values = self.parentApp.taskGraph.tasks

    def beforeEditing(self):
        self.wgId.value   = '{:03d}'.format(self.parentApp.taskGraph.next_sprint_id)
        self.update()

    def on_ok(self):
        if len(self.wgName.value.strip()) == 0:
            npyscreen.notify_confirm("Sprint name must be a unqiue string",editw=1)
            return

        if len(self.wgTasks.value) == 0:
            npyscreen.notify_confirm("Must select at least one goal task for the sprint.",editw=1)
            return

        if self.wgStart.value is None:
            npyscreen.notify_confirm("Must select a start date.",editw=1)
            return

        if self.wgEnd.value is None:
            npyscreen.notify_confirm("Must select a end date.",editw=1)
            return

        if self.wgEnd.value.timestamp() < self.wgStart.value.timestamp():
            npyscreen.notify_confirm("Must select a end date greater after start date.",editw=1)
            return


        sprint_days = (self.wgEnd.value.timestamp() - self.wgStart.value.timestamp())/86400. + 1
        goal_tasks = [self.wgTasks.values[t] for t in self.wgTasks.value]
        task_order = self.parentApp.taskGraph.get_order_of_execution(goal_tasks)
        length = np.sum([self.parentApp.taskGraph.get_task_length(t) for t in task_order])
        if npyscreen.notify_yes_no("Estimated completion time: {:.1f} hours\n".format(length) + \
                "Available work-hours (assuming 8hr days): {:.1f} hours\n".format(sprint_days*8.) + \
                'Suggested task completion order:\n{}'.format(task_order), 
                title="Task proposal", form_color='STANDOUT', wrap=True, editw = 1):
            self.parentApp.taskGraph.add_sprint(self.wgName.value, goal_tasks, self.wgStart.value,self.wgEnd.value)
        self.parentApp.switchFormPrevious()

    def on_cancel(self):
        self.parentApp.switchFormPrevious()

class EditSprint(npyscreen.ActionForm):
    def create(self):
        self.value = None
        self.wgId   = self.add(npyscreen.TitleText, name = "Sprint id:", 
                editable=False)
        self.wgName   = self.add(npyscreen.TitleText, name = "Sprint Name:", editable=False)
        self.wgTitle1   = self.add(npyscreen.TitleText, name = "Involved workers:", editable=False)
        self.wgWorkers   = self.add(WorkerMultiLineAction, max_height=5,scroll_exit=True)

        self.wgGoalTasks = self.add(npyscreen.TitleText,name='Goal tasks:',editable=False)
        self.wgSuggestedTask= self.add(npyscreen.TitleText,name='Suggested next task:',editable=False)

        self.wgTitle1 = self.add(npyscreen.TitleText,name='Involved tasks:',editable=False)
        self.wgColTitles = self.add(npyscreen.GridColTitles,column_width=48 ,col_titles=['new','inprogress','finished'],editable=False,max_height=1)
        self.wgTaskGrid = self.add(npyscreen.SimpleGrid, column_width=48 ,columns=3,scroll_exit=True, max_height=5)

        self.wgCompletion = self.add(npyscreen.TitleText, name = "Completion:", editable=False)

        self.wgStart = self.add(npyscreen.TitleDateCombo, name = "Start Date:")
        self.wgEnd = self.add(npyscreen.TitleDateCombo, name = "End Date:")
        
        self.wgDaysLeft = self.add(npyscreen.TitleText, name = "Days left:", editable=False)

        self.wgEfficiency = self.add(npyscreen.TitleText, name = "Daily gain [Hours saved per day]:", editable=False)
        self.add_handlers({
            "b": self.when_burndown,
            "r": self.when_remove_sprint,
            "e": self.when_task,
            "?": self.when_help
        })
        self.add_handlers({
            "q": self.when_previous,
            })
        self.name = 'Sprint Info'

    def when_previous(self,*args,**kwargs):
        self.parentApp.switchFormPrevious()

    def when_help(self, *args, **kwargs):
        npyscreen.notify_confirm("== Sprints ==\n" + \
                "b display the burndown chart\n" + \
                "r delete this sprint\n" + \
                "e edit a highlighted task\n" + \
                "== General keybindings ==\n" + \
                "q Return to previous screen\n" + \
                "TAB and arrow keys to move around\n" + \
                "Ctrl+c Exit program\n" + \
                "== Further info ==\n" + \
                "All modifcations are auto-saved")

    def when_burndown(self, *args, **kwargs):
        if not self.parentApp.taskGraph.burndown_chart_for_sprint(self.value):
            npyscreen.notify_confirm("No entries to generate burndown from")

    def when_remove_sprint(self, *args, **kwargs):
        if npyscreen.notify_yes_no("Are you sure you want to delete sprint '{}'".format(self.value)):
            self.parentApp.taskGraph.rm_sprint(self.value)
            self.parentApp.switchFormPrevious()

    def when_task(self,*args,**kwargs):
        try:
            task = self.wgTaskGrid.values[self.wgTaskGrid.edit_cell[0]][self.wgTaskGrid.edit_cell[1]]
            if task != '':
                self.parentApp.getForm('EDITTASK').value = task
                self.parentApp.switchForm('EDITTASK')
        except:
            pass



        
    def update(self):
        self.wgId.value = "{:03d}".format(self.parentApp.taskGraph.get_sprint_id_from_sprint(self.value))
        self.wgName.value = '{}'.format(self.parentApp.taskGraph.get_sprint_name_from_sprint(self.value))
        self.wgWorkers.values = self.parentApp.taskGraph.get_workers_from_sprint(self.value)
        

        self.wgGoalTasks.value = " ,".join(self.parentApp.taskGraph.get_goal_tasks_from_sprint(self.value))
        tasks = self.parentApp.taskGraph.get_tasks_from_sprint(self.value)
        self.wgSuggestedTask.value = self.parentApp.taskGraph.suggest_next_task_for_sprint(self.value)
        
        new = []
        ip = []
        f = []
        for t in tasks:
            stat = self.parentApp.taskGraph.get_task_stat(t)
            if stat == 'backlog':
                self.parentApp.taskGraph.update_task_stat(t,'new')
                stat = 'new'
            if stat == 'new':
                new.append(t)
            elif stat == 'inprogress':
                ip.append(t)
            elif stat == 'finished':
                f.append(t)
        max_size = max(len(new),len(ip),len(f))
        new_ = ['']*max_size
        for i,a in enumerate(new):
            new_[i] = a
        ip_ = ['']*max_size
        for i,a in enumerate(ip):
            ip_[i] = a
        f_ = ['']*max_size
        for i,a in enumerate(f):
            f_[i] = a
        values = []
        for r,(b,c,d) in enumerate(zip(new_,ip_,f_)):
            values.append([b,c,d])
        self.wgTaskGrid.values = values
        self.wgTaskGrid.update()
        


        expected_hours = self.parentApp.taskGraph.get_expected_hours_for_sprint(self.value)
        hours = self.parentApp.taskGraph.get_completed_hours_for_sprint(self.value)

        self.wgCompletion.value = "{:.1f} of {:.1f} hours".format(hours,expected_hours)
        days_left = self.parentApp.taskGraph.get_days_left_from_sprint(self.value)
        start,end = self.parentApp.taskGraph.get_dates_from_sprint(self.value)


        self.wgStart.value = start
        self.wgEnd.value = end
        self.wgDaysLeft.value = "{:.1f} days ({:.1f} hours)".format(days_left, days_left*8.)   

        daily_gain = self.parentApp.taskGraph.get_daily_gain_in_sprint(self.value)
        if daily_gain is not None:
            self.wgEfficiency.value = "{:.1f} hours / day".format(daily_gain)
        else:
            self.wgEfficiency.value = "N/A".format(daily_gain)
        
    def beforeEditing(self):
        self.name = "Sprint Info"
        self.update()

    def on_ok(self):
        self.parentApp.taskGraph.update_sprint_start_date(self.value, self.wgStart.value)
        self.parentApp.taskGraph.update_sprint_end_date(self.value, self.wgEnd.value)
        
        self.update()
        self.parentApp.switchFormPrevious()

    def on_cancel(self):
        self.parentApp.switchFormPrevious()




###
# Manage workers

class WorkerMultiLineAction(npyscreen.MultiLineAction):
    def __init__(self, *args, **keywords):
        super(WorkerMultiLineAction, self).__init__(*args, **keywords)

    def actionHighlighted(self, act_on_this, keypress):
        self.parent.parentApp.getForm('EDITWORKER').value = act_on_this#worker
        self.parent.parentApp.switchForm('EDITWORKER')
        
class ManageWorkers(npyscreen.ActionForm):
    def create(self):
        self.wgAdd = self.add(SwitchFormMultiLineAction,values = ['Create new worker'],max_height=2,switch_dict={'Create new worker':'ADDWORKER'},scroll_exit=True)
        self.wgTitle1 = self.add(npyscreen.TitleText,name='Manage workers',editable=False)
        self.wgWorkers   = self.add(WorkerMultiLineAction, values = self.parentApp.taskGraph.workers, max_height=5,scroll_exit=True)

        
        self.add_handlers({
            "?": self.when_help,
        })
        self.add_handlers({
            "q": self.when_previous,
            })

    def when_previous(self,*args,**kwargs):
        self.parentApp.switchFormPrevious()
    def when_help(self, *args, **kwargs):
        npyscreen.notify_confirm(
                "== General keybindings ==\n" + \
                "q Return to previous screen\n" + \
                "TAB and arrow keys to move around\n" + \
                "Ctrl+c Exit program\n" + \
                "== Further info ==\n" + \
                "All modifcations are auto-saved")


    def update(self):
        self.wgWorkers.values = self.parentApp.taskGraph.workers
        self.wgWorkers.update()

    def beforeEditing(self):
        self.update()

    def on_ok(self):
        self.update()
        self.parentApp.switchFormPrevious()

    def on_cancel(self):
        self.parentApp.switchFormPrevious()

class AddWorker(npyscreen.ActionForm):
    def create(self):
        self.wgId   = self.add(npyscreen.TitleText, name = "Worker id:", 
                editable=False)
        self.wgName   = self.add(npyscreen.TitleText, name = "Worker Name:")
        self.add_handlers({
            "q": self.when_previous,
            "?": self.when_help
            })

    def when_help(self, *args, **kwargs):
        npyscreen.notify_confirm(
                "== Workers ==\n" + \
                "You need workers to perform tasks and sprints.\n" + \
                "== General keybindings ==\n" + \
                "q Return to previous screen\n" + \
                "TAB and arrow keys to move around\n" + \
                "Ctrl+c Exit program\n" + \
                "== Further info ==\n" + \
                "All modifcations are auto-saved")


    def when_previous(self,*args,**kwargs):
        self.parentApp.switchFormPrevious()

    def beforeEditing(self):
        self.name = "New Worker"
        self.wgId.value   = '{:03d}'.format(self.parentApp.taskGraph.next_worker_id)
        self.wgName.value = ''

    def on_ok(self):
        self.parentApp.taskGraph.add_worker(self.wgName.value)
        self.parentApp.switchFormPrevious()

    def on_cancel(self):
        self.parentApp.switchFormPrevious()

class EditWorker(npyscreen.ActionForm):
    def create(self):
        self.value = None
        self.wgId   = self.add(npyscreen.TitleText, name = "Worker id:", 
                editable=False)
        self.wgName   = self.add(npyscreen.TitleText, name = "Worker Name:", editable=False)
        self.wgNumTasks = self.add(npyscreen.TitleText, name = "Number of tasks (backlog/new/inprogress/finished):", editable=False)
        self.wgNumSprints = self.add(npyscreen.TitleText, name = "Number of sprints (future/active/finished):", editable=False)
        self.wgNumHours = self.add(npyscreen.TitleText, name = "Hours worked:", editable=False)
        self.wgEfficiency = self.add(npyscreen.TitleText, name = "avg. Efficiency [hours worked/expected]:", editable=False)
        self.wgEntries = self.add(npyscreen.TitleText, name = "Logged entries:", editable=False)
        self.wgColTitles = self.add(npyscreen.GridColTitles,column_width=48 ,col_titles=['Date','Hours','Task'],editable=False,max_height=1)
        self.wgGrid = self.add(npyscreen.SimpleGrid, column_width=48 ,columns=3,scroll_exit=True, max_height=5,select_whole_line=True)
        self.add_handlers({
            "r": self.when_remove_worker,
            "?": self.when_help
        })
        self.add_handlers({
            "q": self.when_previous,
            })
    def when_help(self, *args, **kwargs):
        npyscreen.notify_confirm(
                "== Workers ==\n" + \
                "r delete worker\n" + \
                "== General keybindings ==\n" + \
                "q Return to previous screen\n" + \
                "TAB and arrow keys to move around\n" + \
                "Ctrl+c Exit program\n" + \
                "== Further info ==\n" + \
                "All modifcations are auto-saved")

    def when_previous(self,*args,**kwargs):
        self.parentApp.switchFormPrevious()

    def when_remove_worker(self, *args, **kwargs):
        if npyscreen.notify_yes_no("Are you sure you want to delete worker '{}'".format(self.value)):
            self.parentApp.taskGraph.rm_worker(self.value)
            self.parentApp.switchFormPrevious()

    def update(self):
        self.wgId.value = "{:03d}".format(self.parentApp.taskGraph.get_worker_id_from_worker(self.value))
        self.wgName.value = '{}'.format(self.parentApp.taskGraph.get_worker_name_from_worker(self.value))
        entries = self.parentApp.taskGraph.get_entries_for_worker(self.value)
        self.wgGrid.values = entries
        hours = self.parentApp.taskGraph.get_hours_for_worker(self.value)
        self.wgNumHours.value = "{}".format(hours)
        tasks = self.parentApp.taskGraph.get_tasks_from_worker(self.value)
        num_backlog,num_new,num_inprogress,num_finished=0,0,0,0
        for t in tasks:
            stat = self.parentApp.taskGraph.get_task_stat(t)
            if stat == 'backlog':
                num_backlog += 1
            elif stat == 'new':
                num_new += 1
            elif stat == 'inprogress':
                num_inprogress += 1
            elif stat == 'finished':
                num_finished += 1
        self.wgNumTasks.value = "{}/{}/{}/{}".format(num_backlog, num_new, num_inprogress, num_finished)
        sprints = self.parentApp.taskGraph.get_sprints_from_worker(self.value)
        num_s_future,num_s_active, num_s_finished = 0,0,0
        for s in sprints:
            if self.parentApp.taskGraph.is_sprint_active(s):
                num_s_active += 1
            elif self.parentApp.taskGraph.is_sprint_finished(s):
                num_s_finished += 1
            else:
                num_s_future += 1
        self.wgNumSprints.value = "{}/{}/{}".format(num_s_future,num_s_active,num_s_finished)
        expected_hours = self.parentApp.taskGraph.get_expected_hours_for_worker(self.value)



    def beforeEditing(self):
        self.name = "Worker Info"
        self.update()

    def on_ok(self):
        self.update()
        self.parentApp.switchFormPrevious()

    def on_cancel(self):
        self.parentApp.switchFormPrevious()


###
# Manage tasks

class ManageTasks(npyscreen.ActionForm):
    def create(self):
        self.wgAdd = self.add(SwitchFormMultiLineAction,values = ['Add new task'],max_height=2,
                switch_dict={'Add new task':'ADDTASK'},scroll_exit=True)
        self.wgTitle1 = self.add(npyscreen.TitleText,name='Manage tasks',editable=False)

        self.wgColTitles = self.add(npyscreen.GridColTitles,column_width=48 ,col_titles=['backlog','new','inprogress','finished'],editable=False,max_height=1)
        self.wgGrid = self.add(npyscreen.SimpleGrid, column_width=48 ,columns=4,scroll_exit=True, max_height=5)

        self.add_handlers({
            "e": self.when_edit_task,
            })
        self.add_handlers({
            "q": self.when_previous,
            "?": self.when_help
            })

    def when_help(self, *args, **kwargs):
        npyscreen.notify_confirm(
                "== Tasks ==\n" + \
                "e edit a task\n" + \
                "== General keybindings ==\n" + \
                "q Return to previous screen\n" + \
                "TAB and arrow keys to move around\n" + \
                "Ctrl+c Exit program\n" + \
                "== Further info ==\n" + \
                "All modifcations are auto-saved")

    def when_previous(self,*args,**kwargs):
        self.parentApp.switchFormPrevious()

        

    def when_edit_task(self, *args, **keywords):
        try:
            task = self.wgGrid.values[self.wgGrid.edit_cell[0]][self.wgGrid.edit_cell[1]]
            if task != '':
                self.parentApp.getForm('EDITTASK').value = task
                self.parentApp.switchForm('EDITTASK')
        except:
            pass
                    
    def beforeEditing(self):
        self.update()

    def update(self):
        bl = []
        new = []
        ip = []
        f = []
        for t in self.parentApp.taskGraph.tasks:
            stat = self.parentApp.taskGraph.get_task_stat(t)
            if stat == 'backlog':
                bl.append(t)
            elif stat == 'new':
                new.append(t)
            elif stat == 'inprogress':
                ip.append(t)
            elif stat == 'finished':
                f.append(t)
        max_size = max(len(bl),len(new),len(ip),len(f))
        bl_ = ['']*max_size
        for i,a in enumerate(bl):
            bl_[i] = a
        new_ = ['']*max_size
        for i,a in enumerate(new):
            new_[i] = a
        ip_ = ['']*max_size
        for i,a in enumerate(ip):
            ip_[i] = a
        f_ = ['']*max_size
        for i,a in enumerate(f):
            f_[i] = a
        values = []
        for r,(a,b,c,d) in enumerate(zip(bl_,new_,ip_,f_)):
            values.append([a,b,c,d])
        self.wgGrid.values = values
        self.wgGrid.update()
        
    def on_ok(self):
        self.update()
        self.parentApp.switchFormPrevious()

    def on_cancel(self):
        self.parentApp.switchFormPrevious()


class AddTask(npyscreen.ActionForm):
    def create(self):
        self.dt = self.add(npyscreen.TitleDateCombo, name = "Date:")
        self.wgTask   = self.add(npyscreen.TitleText, name = "Task name:")
        self.wgLen = self.add(npyscreen.TitleSelectOne, value=[0], max_height=5,name = 'Est. duration',
                values  = ['Instant', '1 hour', '2 hours', '4 hours',
                    '1 day', '2 days', '4 days',
                    '1 week','2 weeks','1 month','2 month','4 months','8 months'], scroll_exit=True)
        self.wgWorkers   = self.add(npyscreen.TitleMultiSelect, value=[], max_height=5,
                values = self.parentApp.taskGraph.workers,
                name = "Assigned workers:",
                scroll_exit=True)
        self.wgDeps   = self.add(npyscreen.TitleMultiSelect, value=[], max_height = 5,
                values = self.parentApp.taskGraph.tasks,
                name = "Dependencies:",
                scroll_exit=True)
        self.add(npyscreen.TitleText, name = "Description:",editable=False)
        self.wgDesc = self.add(npyscreen.MultiLineEdit,
               value = """""",
               max_height=5)
        self.add_handlers({
            "?": self.when_help,
        })
        self.add_handlers({
            "q": self.when_previous,
            })

    def when_previous(self,*args,**kwargs):
        self.parentApp.switchFormPrevious()

    def when_help(self, *args, **kwargs):
        npyscreen.notify_confirm(
                "== Tasks ==\n" + \
                "Tasks can be worked on outside of sprints. Logged hours only contribute to sprints when those hours are logged during a sprint and when the worker is assigned to the sprint.\n" + \
                "== General keybindings ==\n" + \
                "q Return to previous screen\n" + \
                "TAB and arrow keys to move around\n" + \
                "Ctrl+c Exit program\n" + \
                "== Further info ==\n" + \
                "All modifcations are auto-saved")

    def update(self):
        self.wgDeps.values = self.parentApp.taskGraph.tasks
        self.wgDeps.update()
        self.wgWorkers.values = self.parentApp.taskGraph.workers
        self.wgWorkers.update()
        self.wgDesc.value = """"""

    def beforeEditing(self):
        self.update()
        self.name = "New Task"
        self.wgTask.value   = ''
        self.dt.value = datetime.today()
        self.wgLen.value = [0]
        self.wgWorkers.value = []
        self.wgDeps.value = []

    def on_ok(self):
        #['Instant', '1 hour', '2 hours', '4 hours',
        # '1 day', '2 days', '4 days',
        # '1 week','2 weeks','1 month',
        # '2 month','4 months','8 months']
        times = [0., 1.,2.,4.,8.,8*2.,8*4.,8*5.,10*8.,20*8.,40*8., 80*8., 160*8.]

        if len(self.wgTask.value.strip()) == 0:
            npyscreen.notify_confirm("Task name must be a unqiue string",editw=1)
            return

        if len(self.wgWorkers.value) == 0:
            npyscreen.notify_confirm("Must select at least one worker",editw=1)
            return
        
        self.parentApp.taskGraph.add_task(
                self.wgTask.value,
                times[self.wgLen.value[0]],
                [self.wgWorkers.values[w] for w in self.wgWorkers.value],
                [self.wgDeps.values[d] for d in self.wgDeps.value],
                self.dt.value,
                self.wgDesc.value)

        self.update()
        self.parentApp.switchFormPrevious()

    def on_cancel(self):
        self.parentApp.switchFormPrevious()

class EditTask(npyscreen.ActionForm):
    def create(self):
        self.value = None
        self.dt = self.add(npyscreen.TitleDateCombo, name = "Date:",editable=False)
        self.wgTask   = self.add(npyscreen.TitleText, name = "Task name:",editable=False)
        self.wgStat  = self.add(npyscreen.TitleText, name = "Status:",editable=False)
        self.wgLen = self.add(npyscreen.TitleSelectOne, value=[0], max_height=5,name = 'Est. duration',
                values  = ['Instant', '1 hour', '2 hours', '4 hours',
                    '1 day', '2 days', '4 days',
                    '1 week','2 weeks','1 month','2 month','4 months','8 months'], scroll_exit=True)
        self.wgWorkers   = self.add(npyscreen.TitleMultiSelect, value=[], max_height=5,
                values = self.parentApp.taskGraph.workers,
                name = "Assigned workers:",
                scroll_exit=True)
        self.wgDeps   = self.add(npyscreen.TitleMultiSelect, value=[], max_height = 5,
                values = self.parentApp.taskGraph.tasks,
                name = "Dependencies:",
                scroll_exit=True)
#        self.wgCompleted = self.add(npyscreen.TitleText, name = "Completion:",editable=False)
        self.wgRem   = self.add(npyscreen.TitleText, name = "Hours left:",editable=False)
        self.wgCompletion = self.add(npyscreen.TitleSlider, out_of=100,editable=False, label = False, name = "Completion:",)
        self.wgHours = self.add(npyscreen.MultiLine,max_height=5,scroll_exit=True)
        self.add(npyscreen.TitleText, name = "Description:",editable=False)
        self.wgDesc = self.add(npyscreen.MultiLineEdit,
                max_height=5)

        self.add_handlers({
            "r": self.when_remove_task,
            "h": self.when_log_hours,
            "H": self.when_rm_hours,
            "f": self.when_finish,
            "?": self.when_help
        })
        self.add_handlers({
            "q": self.when_previous,
            })

    def when_finish(self,*args, **kwargs):
        if npyscreen.notify_yes_no("Are you sure you want to finish task '{}'".format(self.value)):
            self.parentApp.taskGraph.update_task_stat(self.value,'finished',self.dt.value)
            self.parentApp.switchFormPrevious()

        
    def when_rm_hours(self,*args,**kwargs):
        if len(self.wgHours.values) > 0:
            value = self.wgHours.values[self.wgHours.cursor_line]
            entries = self.parentApp.taskGraph.get_hour_entries_for_task(self.value)
            idx = None
            for i,e in enumerate(entries):
                if str(e) == value:
                    idx = i
                    break
            e = str(entries[i])
            entry_id, task_id, date, worker_id, hours, _ = entries[i]
            if npyscreen.notify_yes_no("Are you sure you want to delete hour entry '{}'".format(e)):
                self.parentApp.taskGraph.rm_hours(entry_id)
                self.update()
                

    def when_log_hours(self,*args,**kwargs):
        self.parentApp.getForm("LOGHOURS").value = self.wgTask.value
        self.parentApp.getForm("LOGHOURS").wgDate.value = self.dt.value
        self.parentApp.switchForm("LOGHOURS")

    def when_previous(self,*args,**kwargs):
        self.parentApp.switchFormPrevious()

    def when_remove_task(self, *args, **kwargs):
        if npyscreen.notify_yes_no("Are you sure you want to delete task '{}'".format(self.value)):
            self.parentApp.taskGraph.rm_task(self.value)
            self.parentApp.switchFormPrevious()

    def when_help(self, *args, **kwargs):
        npyscreen.notify_confirm(
                "== Tasks ==\n" + \
                "h log some hours for this task\n" + \
                "f change status to finished\n" + \
                "r remove task\n" + \
                "Tasks can be worked on outside of sprints. Logged hours only contribute to sprints when those hours are logged during a sprint and when the worker is assigned to the sprint. If a finished task get hours added back to it, the task becomes in progress again.\n" + \
                "== General keybindings ==\n" + \
                "q Return to previous screen\n" + \
                "TAB and arrow keys to move around\n" + \
                "Ctrl+c Exit program\n" + \
                "== Further info ==\n" + \
                "All modifcations are auto-saved")
   
    def update(self):
        self.wgHours.values = self.parentApp.taskGraph.get_hour_entries_for_task(self.value)
        self.wgStat.value = self.parentApp.taskGraph.get_task_stat(self.value)
        self.wgDeps.values = self.parentApp.taskGraph.tasks
        self.wgDeps.update()
        self.wgWorkers.values = self.parentApp.taskGraph.workers
        self.wgWorkers.update()
        length = self.parentApp.taskGraph.get_task_length(self.value)
        hours = self.parentApp.taskGraph.get_hours_for_task(self.value)
        self.wgCompletion.out_of = length
        if length == 0.:
            self.wgCompletion.value = 0.
        else:
            self.wgCompletion.value = min(hours/length*100,100)
        self.wgRem.value = "{:.1f} hours".format(length - hours)

        times = [0., 1.,2.,4.,8.,8*2.,8*4.,8*5.,10*8.,20*8.,40*8., 80*8., 160*8.]
        length_idx =  np.searchsorted(times,length)
        self.wgLen.value = length_idx
        length = times[np.searchsorted(times,length)]
#        self.wgCompleted.value = "{:.1f} of {:.1f} hours".format(hours,length)

        v = np.isin(self.wgWorkers.values,self.parentApp.taskGraph.get_workers_from_task(self.value))
        self.wgWorkers.value = list(np.where(v)[0])
        
        v = np.isin(self.wgDeps.values,self.parentApp.taskGraph.get_deps_from_task(self.value))
        self.wgDeps.value = list(np.where(v)[0])
        self.wgDesc.value = """{}""".format(self.parentApp.taskGraph.get_description_from_task(self.value))

    def beforeEditing(self):
        self.name = "Edit Task"
        self.wgTask.value   = self.value
        self.dt.value = datetime.today()
        self.update()
        
    def on_ok(self):
        #['Instant', '1 hour', '2 hours', '4 hours',
        # '1 day', '2 days', '4 days',
        # '1 week','2 weeks','1 month',
        # '2 month','4 months','8 months']
        if len(self.wgTask.value.strip()) == 0:
            npyscreen.notify_confirm("Task name must be a unqiue string")
            return
        if len(self.wgWorkers.value) == 0:
            npyscreen.notify_confirm("Must select at least one worker")
            return
        possible_workers = self.parentApp.taskGraph.workers
        self.parentApp.taskGraph.update_task_workers(
                self.value,
                [self.wgWorkers.values[w] for w in self.wgWorkers.value])
        self.parentApp.taskGraph.update_task_deps(
                self.value,
                [self.wgDeps.values[w] for w in self.wgDeps.value])
        times = [0., 1.,2.,4.,8.,8*2.,8*4.,8*5.,10*8.,20*8.,40*8., 80*8., 160*8.]
        self.parentApp.taskGraph.update_task_length(
                self.value,
                times[self.wgLen.value[0]])
#        self.parentApp.taskGraph.update_task_stat(
#                self.value,
#                self.wgStat.values[self.wgStat.value],
#                self.dt.value)


        self.update()
        self.parentApp.switchFormPrevious()

    def on_cancel(self):
        self.parentApp.switchFormPrevious()

class LogHours(npyscreen.ActionForm):
    def create(self):
        self.value = None
        self.wgDate = self.add(npyscreen.TitleDateCombo, name = "Date:")
        self.wgHours = self.add(npyscreen.TitleText, name = "Hours:",editable=True)
        self.wgTask   = self.add(npyscreen.TitleText, name = "Task name:",editable=False)
        self.wgLen   = self.add(npyscreen.TitleText, name = "Hours left:",editable=False)
        self.wgCompletion = self.add(npyscreen.TitleSlider, out_of=100, name = "Completion:", label=False, editable=False)
        self.wgWorker   = self.add(npyscreen.TitleSelectOne, value=[], max_height=5,
                name = "Worker:",
                scroll_exit=True)
        self.add_handlers({
            "?": self.when_help
        })
        self.add_handlers({
            "q": self.when_previous,
            })

    def when_previous(self,*args,**kwargs):
        self.parentApp.switchFormPrevious()

    def when_help(self, *args, **kwargs):
        npyscreen.notify_confirm(
                "== General keybindings ==\n" + \
                "q Return to previous screen\n" + \
                "TAB and arrow keys to move around\n" + \
                "Ctrl+c Exit program\n" + \
                "== Further info ==\n" + \
                "All modifcations are auto-saved")
  
    def update(self):
        self.wgTask.value = self.value
        length = self.parentApp.taskGraph.get_task_length(self.value)
        hours = self.parentApp.taskGraph.get_hours_for_task(self.value)
        self.wgLen.value = "{:.1f} hours".format(length - hours)
        self.wgCompletion.out_of = length
        if length == 0.:
            self.wgCompletion.value = 0.
        else:
            self.wgCompletion.value = min(hours/length*100,100)
                
        self.wgWorker.values = self.parentApp.taskGraph.get_workers_from_task(self.value)


    def beforeEditing(self):
        self.name = "Log Hours"
        self.wgTask.value   = self.value
        self.wgDate.value = datetime.today()
        self.wgHours.value = ''
        self.update()
        
    def on_ok(self):
        #['Instant', '1 hour', '2 hours', '4 hours',
        # '1 day', '2 days', '4 days',
        # '1 week','2 weeks','1 month',
        # '2 month','4 months','8 months']
        if len(self.wgTask.value.strip()) == 0:
            npyscreen.notify_confirm("Task name must be a unqiue string")
            return

        if len(self.wgHours.value.strip()) == 0:
            npyscreen.notify_confirm("Must enter some number for hours")
            return

        if len(self.wgWorker.value) == 0:
            npyscreen.notify_confirm("Must select a worker")
            return
        try:
            hours = float(self.wgHours.value)
        except:
            npyscreen.notify_confirm("Hours must be a number")
            return
        if hours <= 0.:
            npyscreen.notify_confirm("Hours must be positive.")
            return

        self.parentApp.taskGraph.add_hours(
                self.value,
                self.wgDate.value,
                self.wgWorker.values[self.wgWorker.value[0]],
                hours)

        self.update()
        self.parentApp.switchFormPrevious()

    def on_cancel(self):
        self.parentApp.switchFormPrevious()

class ScrumApplication(npyscreen.NPSAppManaged):
    """
    Start screen prompts to load a file, or make new
    then displays tasks, workers and stats
    Ctrl+t -> adds task
    Ctrl+w -> adds worker
    """
    def onStart(self):
        self.taskGraph = TaskGraph('database.db',new=False)
#        self.taskGraph.add_worker('admin')
#        self.taskGraph.add_task('a',40., 1,[])
#        self.taskGraph.add_task('b',1., 1,['a'])
#        self.taskGraph.add_hours('a',datetime.today(),1,3.)
#        self.taskGraph.add_sprint('test','a',datetime.today(),datetime.today())
        self.addForm("MAIN", RecordListDisplay)

        self.addForm("ADDTASK",AddTask)
        self.addForm("EDITTASK",EditTask)
        self.addForm("ADDSPRINT",AddSprint)
        self.addForm("EDITSPRINT",EditSprint)
        self.addForm("ADDWORKER",AddWorker)
        self.addForm("EDITWORKER",EditWorker)
        self.addForm("LOGHOURS",LogHours)
        self.addForm("MANAGETASKS",ManageTasks)
        self.addForm("MANAGEWORKERS",ManageWorkers)
        self.addForm("MANAGESPRINTS",ManageSprints)
    def run(self):
        try:
            super(ScrumApplication,self).run()
        except KeyboardInterrupt:
            print("Goodbye!")

 
if __name__ == '__main__':
    myApp = ScrumApplication()
    myApp.run()
