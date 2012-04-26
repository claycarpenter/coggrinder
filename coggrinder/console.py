"""
Created on Mar 22, 2012

@author: clay
"""
from coggrinder.entities.tasks import TaskList, Task
from coggrinder.task_services import TaskListService, TaskService
from coggrinder.authentication import AuthenticationService
import apiclient.discovery
import random

# TODO: Refactor this by moving it to utilities.ConsoleTest.
class ConsoleTestUtil(object):
    @classmethod
    def create_gtasks_service_proxy(cls):
        auth_service = AuthenticationService()
        authorized_http = auth_service.authenticate_connection()
        gtasks_service_proxy = apiclient.discovery.build("tasks", "v1",
            http=authorized_http)
        
        return gtasks_service_proxy
    
    @classmethod
    def create_tasklist_service(cls):        
        tasklist_service = TaskListService(cls.create_gtasks_service_proxy().tasklists())
        
        return tasklist_service
    
    @classmethod
    def create_task_service(cls):
        task_service = TaskService(cls.create_gtasks_service_proxy().tasks())
        
        return task_service
    
    @staticmethod
    def test_get_tasklist(tasklist_service, tasklist_id="MTM3ODEyNTc4OTA1OTU2NzE3NTM6MDow"):
        tasklist = tasklist_service.get_tasklist(tasklist_id)
        print "Retrieved tasklist: {0}".format(tasklist)
        
        return tasklist
        
    @staticmethod
    def test_get_task(task_service,
        tasklist,
        task_id="MTM3ODEyNTc4OTA1OTU2NzE3NTM6MTgzNjY0NTg2MToyMDQxODc3NTk3"):
        task = task_service.get_task(tasklist, task_id)
        
        print "Retrieved task: {0}".format(task)
        
        return task
    
    @staticmethod
    def test_all_tasklists(tasklist_service):
        all_tasklists = tasklist_service.get_all_tasklists()
        print "Found {0} tasklists:".format(len(all_tasklists))
        for current_tasklist in all_tasklists:
            print " - Tasklist: {0}".format(current_tasklist)
            
        return all_tasklists
    
    @staticmethod
    def test_get_tasks_in_tasklist(task_service, tasklist):
        all_tasks = task_service.get_tasks_in_tasklist(tasklist)
        print "Found {0} tasks:".format(len(all_tasks))
        
        for current_task in all_tasks:
            print " - Task: {0}".format(current_task)
            
        return all_tasks
    
    @staticmethod
    def test_add_task(task_service, tasklist):
        task = Task(title="Test Add Task Item")
        
        print "Adding this task: {0}".format(task)
        task = task_service.add_task(tasklist, task)
        
        return task
            
    @staticmethod
    def test_add_tasklist(tasklist_service):
        tasklist = TaskList(title="Test Add TaskList")
        
        print "Adding this tasklist: {0}".format(tasklist)
        tasklist = tasklist_service.add_tasklist(tasklist)
        print "Received this updated tasklist: {0}".format(tasklist)
        
        return tasklist
    
    @staticmethod
    def test_delete_tasklist(tasklist_service, tasklist_id):
        tasklist = tasklist_service.get_tasklist(tasklist_id)
        print "Confirmed existence of tasklist: {0}".format(tasklist)
        
        tasklist_service.delete_tasklist(tasklist)
        print "Deleted tasklist: {0}".format(tasklist)
    
    @staticmethod
    def test_delete_task(task_service, tasklist, task):
        task = task_service.get_task(tasklist, task.entity_id)
        print "Confirmed existence of task: {0}".format(task)
        
        task = task_service.delete_task(tasklist, task)
        print "Deleted task: {0}".format(task)
    
    @staticmethod
    def test_update_task(task_service, tasklist, task):
        task = task_service.get_task(tasklist, task.entity_id)
        print "Confirmed existence of task: {0}".format(task)
        
        task.title = task.title + " Updated"
        print "Sending updated task: {0}".format(task)
        
        task = task_service.update_task(tasklist, task)
        print "Updated task: {0}".format(task)
        
        return task
    
    @staticmethod
    def test_update_tasklist(tasklist_service, tasklist_id):
        tasklist = tasklist_service.get_tasklist(tasklist_id)
        print "Confirmed existence of tasklist: {0}".format(tasklist)
        
        tasklist.title = tasklist.title + " Updated"
        print "Sending updated tasklist: {0}".format(tasklist)
        
        tasklist = tasklist_service.update_tasklist(tasklist)
        print "Updated tasklist: {0}".format(tasklist)
        
        return tasklist

    @staticmethod
    def test_tasklist_service():    
        tasklist_service = ConsoleTestUtil.create_tasklist_service()
    
        print "Test get >>>"    
        ConsoleTestUtil.test_get_tasklist(tasklist_service)
        
        print "Test list >>>"
        ConsoleTestUtil.test_all_tasklists(tasklist_service)
        
        print "Test add, list >>>"
        new_tasklist = ConsoleTestUtil.test_add_tasklist(tasklist_service)
        
        ConsoleTestUtil.test_all_tasklists(tasklist_service)
        
        print "Test get, delete, list >>>"
        ConsoleTestUtil.test_get_tasklist(tasklist_service, new_tasklist.entity_id)
        
        ConsoleTestUtil.test_delete_tasklist(tasklist_service, new_tasklist.entity_id)
        
        ConsoleTestUtil.test_all_tasklists(tasklist_service)
        
        print "Test add, update, delete, list >>>"
        new_tasklist = ConsoleTestUtil.test_add_tasklist(tasklist_service)
        
        new_tasklist = ConsoleTestUtil.test_update_tasklist(tasklist_service, new_tasklist.entity_id)
        
        ConsoleTestUtil.test_delete_tasklist(tasklist_service, new_tasklist.entity_id)
        
        ConsoleTestUtil.test_all_tasklists(tasklist_service)
        
    @staticmethod
    def test_task_service():
        task_service = ConsoleTestUtil.create_task_service()
        tasklist_service = ConsoleTestUtil.create_tasklist_service()
        
        tasklist = ConsoleTestUtil.test_get_tasklist(tasklist_service,
            tasklist_id="MTM3ODEyNTc4OTA1OTU2NzE3NTM6MTgzNjY0NTg2MTow")
        
        assert tasklist is not None
                
        print "Test list >>>"
        all_tasks = ConsoleTestUtil.test_get_tasks_in_tasklist(task_service, tasklist)
        
        assert len(all_tasks) > 0
        
        # Pick a random task from the tasklist
        random_task = random.choice(all_tasks)
        
        print "Test get >>>"
        print "Retrieving random task with id: {0} and tasklist id {1}".format(
            random_task.entity_id, tasklist.entity_id)
        random_task = ConsoleTestUtil.test_get_task(task_service,tasklist, 
            random_task.entity_id)
                        
        print "Test add, update, delete, list >>>"
        new_task = ConsoleTestUtil.test_add_task(task_service, tasklist)
        
        new_task = ConsoleTestUtil.test_update_task(task_service, tasklist, new_task)
        
        new_task = ConsoleTestUtil.test_delete_task(task_service, tasklist, new_task)
        
        ConsoleTestUtil.test_get_tasks_in_tasklist(task_service, tasklist)

if __name__ == "__main__":
#    print "Running TaskListService tests..."
#    ConsoleTestUtil.test_tasklist_service()
    
    print "\n\nRunning TaskService tests..."
    ConsoleTestUtil.test_task_service()

