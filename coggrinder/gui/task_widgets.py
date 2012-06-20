"""
Created on Mar 29, 2012

@author: Clay Carpenter
"""
from gi.repository import Gtk
from gi.repository import GObject
from coggrinder.entities.tasktree import TreeTask, TreeTaskList
from coggrinder.resources.icons import buttons
from coggrinder.gui.events import Event, EventRegistry, eventListener, eventAware
from coggrinder.gui.task_treestore import TaskTreeStore, TaskTreeStoreNode
from coggrinder.entities.tasktree import TaskTree
import copy
import pprint
from operator import itemgetter
from logging import debug, debug as temp_debug
from coggrinder.services.task_services import UnregisteredEntityError
from coggrinder.log_utilities import entryExit
from coggrinder.entities.properties import TaskStatus

class TaskTreeEvents(object):
    SAVE = "save"
    SYNC = "sync"
    REVERT = "revert"
    
    ADD_TASKLIST = "add_tasklist"
    DELETE_TASKLIST = "delete_tasklist"
    
    ADD_TASK = "add_task"
    EDIT_TASK = "edit_task"
    COMPLETE_TASK = "complete_task"
    DELETE_TASK = "delete_task"
    
    PROMOTE_TASK = "promote_task"
    DEMOTE_TASK = "demote_task"
    REORDER_TASK_UP = "reorder_task_up"
    REORDER_TASK_DOWN = "reorder_task_down"   
    
    OPEN_CONFIG_WINDOW = "open_config_window" 

@eventAware
class TaskTreeWindowController(object):
    def __init__(self, tasktree_service=None):
        self._tasktree_service = tasktree_service

        # Initialize the TaskTreeWindow Gtk window that serves as the view
        # for this controller.
        self.view = TaskTreeWindow()

        # Connect to entity title update event (the second/final stage of a 
        # title edit process).
        self.view.entity_title_edited.register(self._handle_entity_title_updated)
        
        # Placeholder for a timeout/callback ID. Allows for addressing and
        # canceling a recurring timeout if necessary. 
        self._timeout_id = None
        
    @property
    def tasktree_service(self):
        return self._tasktree_service
        
    @property
    def treeview_state_manager(self):
        return self.view.treeview_state_manager

    def refresh_task_data(self):
        """Pull updated tasklist and task information from the task tree
        services; Store the updated results locally.
        """
        # Pull updated task data (tasklists and tasks) from the services.
        self.tasktree_service.refresh_task_data()

    @entryExit()
    def update_view(self):        
        self.view.update_view(self.tasktree_service.tree)               
        
    def build_task_view_model(self):
        # Build the task tree view from a the TaskTreeService's TaskTree 
        # task data set.
        self.view.build_tasktree(self.tasktree_service.tree)

    @eventListener(event_name=TaskTreeEvents.SAVE)
    def _handle_save_event(self, button):
        raise NotImplementedError
        self.tasktree_service.push_task_data()

    @eventListener(event_name=TaskTreeEvents.SYNC)
    def _handle_sync_event(self, button):
        raise NotImplementedError
        self.tasktree_service.pull_task_data()

    @eventListener(event_name=TaskTreeEvents.REVERT)
    def _handle_revert_event(self, button):        
        # Clear away any user changes.
        self.tasktree_service.revert_task_data()
        
        # Clear away any existing tree state (selections, expansions, etc.).
        self.treeview_state_manager.clear_all_states()
        
        # Update the UI.
        self.update_view()

    @eventListener(event_name=TaskTreeEvents.ADD_TASKLIST)
    def _handle_add_tasklist_event(self, button):        
        # Create the new (blank) TaskList, and add it to the task data.
        new_tasklist = self.tasktree_service.add_tasklist()
        
        # Clear any existing selections. Select the new TaskList and set the 
        # tree node (title) to be "editable". 
        self.treeview_state_manager.set_entity_editable(new_tasklist)

        # Refresh the UI.
        self.view.update_view(self.tasktree_service.tree)

    @eventListener(event_name=TaskTreeEvents.DELETE_TASKLIST)
    def _handle_delete_tasklist_event(self, button):
        # Locate the selected TaskList.
        selected_tasklists = self.treeview_state_manager.selected_tasklists
        assert len(selected_tasklists) == 1, "Should only allow a single TaskList to be selected for deletion."
        targeted_tasklist = selected_tasklists[0]

        # Delete the TaskList.
        self.tasktree_service.delete_entity(targeted_tasklist)

        # Update the UI.
        self.update_view()

    @eventListener(event_name=TaskTreeEvents.ADD_TASK)
    @entryExit()
    def _handle_add_task_event(self, button):
        # Find the ID of the selected parent entity. This will determine the 
        # new tasks's parent TaskList and, optionally, it's parent Task as well.
        selected_entities = self.treeview_state_manager.selected_entities
        assert len(selected_entities) == 1, "Should only allow a single TaskList or Task to be selected as a parent for the new Task."
        parent_entity = selected_entities.pop()
              
        # Determine the new Task's TaskList and parent Task, if appropriate.      
        try:
            # Get the TaskList ID from the parent Task.
            tasklist = parent_entity.tasklist
            parent_task = parent_entity
        except AttributeError:
            # Get the TaskList ID from the parent TaskList. As a direct child 
            # of the TaskList, the Task will have no parent ID.
            tasklist = parent_entity
            parent_task = None

        # Create an empty new Task with only the parent ID and TaskList ID 
        # specified. By default, this Task will be the lowest ordered Task 
        # in its sibling group.
        new_task = self.tasktree_service.add_task(tasklist, parent_task=parent_task, title="")
        
        # Sort the TaskTree to ensure proper positioning of the new task.
        self.tasktree_service.sort()
        
        temp_debug("Created new task: {0}".format(new_task))
        
        # Clear any existing selections. Select the new Task and set the 
        # tree node (title) to be "editable". 
        self.treeview_state_manager.set_entity_editable(new_task)
        
        # Ensure that any parent nodes of the new Task are also expanded.
        task = new_task
        temp_debug("Expanding parent nodes to expose: {0}".format(task))
        while task.parent_task is not None:
            task = task.parent_task
            temp_debug("\tExpanding (parent) T node: {0}".format(task))
            self.treeview_state_manager.expand_entity(task)

        # Ensure the TaskList is expanded.
        temp_debug("\tExpanding TL node: {0}".format(tasklist))
        self.treeview_state_manager.expand_entity(tasklist)

        # Update the UI.
        self.update_view()
        
    @eventListener(event_name=TaskTreeEvents.EDIT_TASK)
    def _handle_edit_task_details_event(self, button):
        raise NotImplementedError
    
        # Locate the selected Task.
        selected_tasks = self.treeview_state_manager.selected_tasks
        assert len(selected_tasks) > 0, "At least one Task must be selected for editing."        

        """
        What details can be modified in bulk?
            - Due date
            - Description? I could see this being useful if you wanted to 
            apply a generic description, or some kind of tag/meta-info to a 
            bunch of Tasks.
            - Completion? This can also be achieved via the 
            complete/uncomplete UI action.
        """
        # Collect updated details information in a dedicated UI.
        task_details_window = TaskDetailsWindow()
        task_details_window.show()
        
        updated_task_details = task_details_window.task_details
        
        # Update each modified entity with the new details.
        for task in selected_tasks:
            # Apply updated details to the Task.
            if updated_task_details.status:
                task.status = updated_task_details.status
            if updated_task_details.due_date:
                task.due_date = updated_task_details.due_date
            if updated_task_details.description:
                task.description = updated_task_details.description
            
            # Push the Task update into the TaskTree.
            self.tasktree_service.update_entity(task)
        
        # Update the UI.
        self.update_view()

    @eventListener(event_name=TaskTreeEvents.COMPLETE_TASK)
    def _handle_complete_task_event(self, button):
        raise NotImplementedError
    
        # Locate the selected task or tasks.
        selected_tasks = self.treeview_state_manager.selected_tasks
        assert len(selected_tasks) > 0
        
        # Determine what the final task status will be for the selected Tasks.
        # If all Tasks have the same status, toggle it. If they have a mix
        # (complete and incomplete), then set them all to complete.
        final_task_status = selected_tasks[0]
        for selected_task in selected_tasks:
            if final_task_status == selected_task.task_status:
                continue
            else:
                final_task_status = TaskStatus.COMPLETED
        
        # For each Task, update the Task with the new status and push the 
        # updated Task into the TaskTree.
        for selected_task in selected_tasks:
            selected_task.task_status = final_task_status
            
            self.tasktree_service.update_entity(selected_task)
            
        # Update the UI.
        self.update_view()

    @eventListener(event_name=TaskTreeEvents.DELETE_TASK)
    def _handle_delete_task_event(self, button):
        raise NotImplementedError
    
        # Locate the selected task or tasks.
        selected_tasks = self.treeview_state_manager.selected_tasks
        assert len(selected_tasks) > 0
        
        # For each task, delete the task. The service layer will handle 
        # promoting any children of the task to 
        # be children of the task's parent (task or tasklist).
        # Keep track of the child tasks that have their parent updated, as 
        # they will need to be updated as well.
        for selected_task in selected_tasks:
            self.tasktree_service.delete_entity(selected_task)

        # Update the UI.
        self.update_view()

    @eventListener(event_name=TaskTreeEvents.PROMOTE_TASK)
    def _handle_promote_task_event(self, button):
        raise NotImplementedError
    
        # Locate the selected task or tasks.
        selected_tasks = self.treeview_state_manager.selected_tasks
        assert len(selected_tasks) > 0
        
        # Promote all of the selected Tasks.
        self.tasktree_service.promote(*selected_tasks)
        
        # Update the UI.
        self.update_view()

    @eventListener(event_name=TaskTreeEvents.DEMOTE_TASK)
    def _handle_demote_task_event(self, button):
        raise NotImplementedError
    
        # Locate the selected task or tasks.
        selected_tasks = self.treeview_state_manager.selected_tasks
        assert len(selected_tasks) > 0
        
        # Demote all of the selected Tasks.
        self.tasktree_service.demote(*selected_tasks)
        
        # Update the UI.
        self.update_view()

    @eventListener(event_name=TaskTreeEvents.REORDER_TASK_UP)
    def _handle_reorder_task_up_event(self, button):
        raise NotImplementedError
    
        # Locate the selected task or tasks.
        selected_tasks = self.treeview_state_manager.selected_tasks
        assert len(selected_tasks) > 0
        
        # Reorder all of the selected Tasks up ("higher priority").
        self.tasktree_service.reorder_task_up(*selected_tasks)
        
        # Update the UI.
        self.update_view()

    @eventListener(event_name=TaskTreeEvents.REORDER_TASK_DOWN)
    def _handle_reorder_task_down_event(self, button):
        raise NotImplementedError
    
        # Locate the selected task or tasks.
        selected_tasks = self.treeview_state_manager.selected_tasks
        assert len(selected_tasks) > 0
        
        # Reorder all of the selected Tasks down ("lower priority").
        self.tasktree_service.reorder_task_down(*selected_tasks)
        
        # Update the UI.
        self.update_view()

    """
    TODO: This is just a dummy button at this point. Its presence anticipates
    some future configuration screen (likely configuring between local and 
    Google/remote task data storage.
    """ 
    @eventListener(event_name=TaskTreeEvents.OPEN_CONFIG_WINDOW)
    def _handle_configure_event(self, button):
        raise NotImplementedError

    def _handle_entity_title_updated(self, target_entity_id, updated_title):
        # Get the entity from the TaskTreeService.
        target_entity = self.tasktree_service.get_entity_for_id(target_entity_id)
        
        # Set the entity's updated title.
        target_entity.title = updated_title
      
        # Send the updated entity to the TaskTreeService.
        target_entity = self.tasktree_service.update_entity(target_entity)
        
        # Clear the editable tree state for the target entity.
        self.treeview_state_manager.clear_editable(target_entity)
        
        # Reorder the tree.
        self.tasktree_service.sort() 

        # Update the task data view.
        self.update_view()   

    def show(self):
        self.update_view()
        self.view.show_all()
    
    def clear_treeview_state(self):
        self.view.clear_treeview_state()
    
    def clear_treeview_selections(self):
        self.view.clear_treeview_selections()
#------------------------------------------------------------------------------ 

class TaskTreeWindow(Gtk.Window):
    """
    Maintain the integrity of the view.

    Does not need to expose selection _events_ to outside listeners, as these
    (currently) aren't linked to a user action. It does need to expose the
    selection state, however, in order to allow listening controllers to react
    to other events that depend on the context provided by the user's
    selection.
    """
    def __init__(self):
        Gtk.Window.__init__(self, title="CogGrinder")

        self.set_default_size(400, 400)
        self.connect("delete-event", Gtk.main_quit)

        # Set up the primary window components: the toolbar at the top of the
        # screen, with the task tree filling the remaining space.
        self._base_layout = Gtk.VBox(spacing=0)
        self.add(self._base_layout)

        # Add the toolbar.
        self.toolbar_controller = TaskToolbarViewController()
        self._base_layout.pack_start(self.toolbar_controller.view, False, False, 0)

        # Add the task tree controller and view.        
        self.treeview_controller = TaskTreeViewController()
        scrolling_window = Gtk.ScrolledWindow()
        scrolling_window.add(self.treeview_controller.view)
        self._base_layout.pack_end(scrolling_window, True, True, 0)

        # Propagate task tree title edited event.
        self.entity_title_edited = Event.propagate(
            self.treeview_controller.entity_title_edited)

        # Connect to the selection changed event from the TreeView.
        self.treeview_controller.selection_state_changed.register(self.toolbar_controller.selection_state_changed)
    
    @property
    def treeview_state_manager(self):
        return self.treeview_controller.treeview_state_manager
        
    def _request_editing_callback(self):
        debug("Setting editing (timeout) callback.")
        self._timeout_id = GObject.timeout_add(100, self._start_editing_callback)
        debug("Editing timeout created with ID {id}".format(id=self._timeout_id))  
        
    def _start_editing_callback(self):
        self.is_treeview_change_ignored = True
        self.treeview_controller.start_editing()        
        self.is_treeview_change_ignored = False
        
        # This is a callback method started with GObject.timeout_add. In 
        # order to prevent the function from being called again, False is 
        # returned.
        return False
    
    def update_tasktree_model(self, tasktree):
        self.treeview_controller.update_tasktree_model(tasktree)
        
    def build_tasktree(self, tasktree):
        self.treeview_controller.build_tasktree(tasktree)
    
    def set_treeview_change_event_ignored(self, ignore):
        self.treeview_controller.is_treeview_change_ignored = ignore
    
    def clear_treeview_state(self):
        self.treeview_controller.clear_treeview_state()
    
    def refresh_treeview_state(self):
        self.treeview_controller.refresh_treeview_state()
        
    def restore_treeview_state(self):
        self.treeview_controller.update_treeview_state()
            
    def clear_treeview_selections(self):
        self.treeview_controller.clear_treeview_selections()
        
    def update_button_states(self):
        """
        TODO: This may be digging to deep into the TreeViewController's
        sphere.
        """ 
        self.toolbar_controller.selection_state_changed(
            self.treeview_controller.treeview_state_manager.tasklist_selection_state,
            self.treeview_controller.treeview_state_manager.task_selection_state)
        
    def update_view(self, updated_tasktree):        
        # Update tree view.
        self.treeview_controller.update_view(updated_tasktree)        
        
        debug("TreeView state after update view: {0}".format(self.treeview_state_manager))
        
        # Update the toolbar button states.
        debug("Updating button states.")
        self.update_button_states()
        
        """
        Can this be accomplished by only looking at the info held by TVStMngr?
        """
        # Register/start any needed callbacks.
        if self.treeview_state_manager.has_editable_entity():
            self._request_editing_callback()            
#------------------------------------------------------------------------------ 

class TaskToolbarViewController(object):
    """
    Listens for selection change events, and sends this information to the
    view.

    Converts UI button events into domain events.
    """
    """
    TODO: This init method may no longer be relevant.
    """
    def __init__(self):        
        self.view = TaskToolbarView()

    def selection_state_changed(self, tasklist_selection_state, task_selection_state):
        self.view.update_button_states(tasklist_selection_state, task_selection_state)
#------------------------------------------------------------------------------ 

class TaskToolbarView(Gtk.HBox):
    """
    Builds the toolbar buttons.

    Manages toolbar enabled/disabled state.
    """
    def __init__(self):
        Gtk.HBox.__init__(self, spacing=10)

        # Set up the toolbar by function group.
        # Set up persistence buttons.
        self.pack_start(self._build_persistence_buttons(), False, False, 5)

        # Set up list/folder buttons.
        self.pack_start(self._build_list_buttons(), False, False, 5)

        # Set up task buttons.
        self.pack_start(self._build_task_buttons(), False, False, 5)

        # Set up task organization buttons.
        self.pack_start(self._build_task_organization_buttons(), False, False, 5)

        # Set up configuration buttons.
        self.pack_end(self._build_configuration_buttons(), False, False, 5)

    # TODO: A lot of this button building code is redundant.
    def _build_persistence_buttons(self):
        """
        Builds buttons for:
        -- Save/persist
        -- Sync with (Google) server
        -- Revert changes
        """
        button_box = Gtk.HBox(spacing=5)

        """
        TODO: Currently setting the revert and save buttons to be enabled by
        default.
        In the future, these should only be enabled when there are outstanding
        changes on the current task data set.
        """
        self.save_button = BinaryIconButton(TaskTreeEvents.SAVE, buttons.FILES["save.png"], is_enabled=True)
        button_box.add(self.save_button)

        self.sync_button = BinaryIconButton(TaskTreeEvents.SYNC, buttons.FILES["sync.png"])
        button_box.add(self.sync_button)

        self.revert_button = BinaryIconButton(TaskTreeEvents.REVERT, buttons.FILES["revert.png"], is_enabled=True)
        button_box.add(self.revert_button)

        return button_box

    def _build_list_buttons(self):
        """
        Builds buttons for:
        -- Add new list
        -- Delete existing list
        """
        button_box = Gtk.HBox(spacing=5)

        self.add_list_button = BinaryIconButton(TaskTreeEvents.ADD_TASKLIST, buttons.FILES["folder_plus.png"])
        button_box.add(self.add_list_button)

        self.delete_list_button = BinaryIconButton(TaskTreeEvents.DELETE_TASKLIST, buttons.FILES["folder_delete.png"], is_enabled=False)
        button_box.add(self.delete_list_button)

        return button_box

    def _build_task_buttons(self):
        """
        Builds buttons for:
        -- Add new task
        -- Edit selected task(s)
        -- Complete selected task(s)
        -- Remove selected task(s)
        """
        button_box = Gtk.HBox(spacing=5)

        self.add_task_button = BinaryIconButton(TaskTreeEvents.ADD_TASK, buttons.FILES["doc_plus.png"], is_enabled=False)
        button_box.add(self.add_task_button)

        self.edit_task_button = BinaryIconButton(TaskTreeEvents.EDIT_TASK, buttons.FILES["doc_edit.png"], is_enabled=False)
        button_box.add(self.edit_task_button)

        self.complete_task_button = BinaryIconButton(TaskTreeEvents.COMPLETE_TASK, buttons.FILES["checkbox_checked.png"], is_enabled=False)
        button_box.add(self.complete_task_button)

        self.delete_task_button = BinaryIconButton(TaskTreeEvents.DELETE_TASK, buttons.FILES["doc_delete.png"], is_enabled=False)
        button_box.add(self.delete_task_button)

        return button_box

    def _build_task_organization_buttons(self):
        """
        Builds buttons for:
        -- Promote task
        -- Demote task
        -- Reorder task up(ward)
        -- Reorder task down(ward)
        """
        button_box = Gtk.HBox(spacing=5)

        self.promote_task_button = BinaryIconButton(TaskTreeEvents.PROMOTE_TASK, buttons.FILES["sq_br_prev.png"], is_enabled=False)
        button_box.add(self.promote_task_button)

        self.demote_task_button = BinaryIconButton(TaskTreeEvents.DEMOTE_TASK, buttons.FILES["sq_br_next.png"], is_enabled=False)
        button_box.add(self.demote_task_button)

        self.reorder_task_up_button = BinaryIconButton(TaskTreeEvents.REORDER_TASK_UP, buttons.FILES["sq_br_up.png"], is_enabled=False)
        button_box.add(self.reorder_task_up_button)

        self.reorder_task_down_button = BinaryIconButton(TaskTreeEvents.REORDER_TASK_DOWN, buttons.FILES["sq_br_down.png"], is_enabled=False)
        button_box.add(self.reorder_task_down_button)

        return button_box

    def _build_configuration_buttons(self):
        """
        Builds buttons for:
        -- Configure program options
        """
        button_box = Gtk.HBox(spacing=5)

        self.configure_button = BinaryIconButton(TaskTreeEvents.OPEN_CONFIG_WINDOW, buttons.FILES["cog.png"])
        button_box.add(self.configure_button)

        return button_box

    """
    This would be hard to move to the toolbar view because it requires
    checking the selection state of the TaskTreeView.
    """
    def update_button_states(self, tasklist_selection_state, task_selection_state):        
        # Only enable when single TaskList is selected.
        self.delete_list_button.set_state(
            tasklist_selection_state == TaskTreeSelectionState.SINGLE)

        # Only show add task when a single row/entity--either task or 
        # TaskList--is selected:
        # -- Task single and TaskList none or
        # -- Task none and TaskList single
        add_task_button_enabled = False
        if ((task_selection_state == TaskTreeSelectionState.SINGLE and tasklist_selection_state == TaskTreeSelectionState.NONE) 
            or (task_selection_state == TaskTreeSelectionState.NONE and tasklist_selection_state == TaskTreeSelectionState.SINGLE)):
            add_task_button_enabled = True
            
        self.add_task_button.set_state(add_task_button_enabled)

        # Show whenever task or tasks are selected, regardless of tasklist.
        task_detail_buttons_enabled = False
        if task_selection_state != TaskTreeSelectionState.NONE:
            task_detail_buttons_enabled = True
        self.edit_task_button.set_state(task_detail_buttons_enabled)
        self.complete_task_button.set_state(task_detail_buttons_enabled)
        self.delete_task_button.set_state(task_detail_buttons_enabled)
        self.promote_task_button.set_state(task_detail_buttons_enabled)
        self.demote_task_button.set_state(task_detail_buttons_enabled)
        self.reorder_task_up_button.set_state(task_detail_buttons_enabled)
        self.reorder_task_down_button.set_state(task_detail_buttons_enabled)
#------------------------------------------------------------------------------ 

class TaskTreeViewController(object):
    """Provides an interface to the task tree view.

    Converts task tree paths into
    usable entity lists to be consumed by the parent controller. Converts
    entity lists into new tree stores and displays the updated information.

    Manages tree state: selections, selection state, and expansion state.
    """
    def __init__(self, tasktree=None):        
        if tasktree is None:
            tasktree = TaskTree()
        self._tasktree = tasktree

        # Establish the tree store (model) that holds the task entity 
        # information.
        self.task_treestore = TaskTreeStore()

        # Declare the selection changed and title edited events.
        self.selection_state_changed = Event()
        self.entity_title_edited = Event()
        
        self.is_treeview_change_ignored = False
        
        # Create an initial, blank TreeView state.
        self.treeview_state_manager = TaskTreeViewStateManager()
        
        # Initialize the view.
        self._initialize_view()

    def _initialize_view(self):        
        self.view = TaskTreeView()
        
        # TODO: Connect edited and (selection) changed event handlers.
        self.view.title_renderer.connect("edited", self._handle_cell_edited)

        # Monitor selection change events.
        self.view.get_selection().connect("changed",
            self._handle_selection_changed)

        # Monitor tree expansion/collapse change events.
        self.view.connect("row-expanded", self._handle_row_expanded)
        self.view.connect("row-collapsed", self._handle_row_collapsed)
        
        # Connect the tree store/row_data to the tree view.
        self.view.set_model(self.task_treestore)
        
    def build_tasktree(self, tasktree):
        # Build a new TaskTreeStore (Gtk TreeStore) with the updated task data.
#        self._tasktree = copy.deepcopy(tasktree)
        self._tasktree = tasktree
        self.task_treestore.build_tree(self._tasktree)      
    
    def update_tasktree_model(self, updated_tasktree):
        """Collect the current tree state, replace the tree model, and then
        restore the tree state (as much as possible).
        """
        
#        # Collect the current TreeView state (what is selected, expanded).
#        self.collect_treeview_state()
        
        # Pass the updates along to the task tree store.
        self.build_tasktree(updated_tasktree)
        
        # Update the tree states by informing the TreeViewStateMngr of changes
        # to the task data that affect tree state information.
        self.update_tree_states(updated_tasktree)
        
        # The tree view state was destroyed as the old tree was built. Refresh
        # back to the correct state.
        self.update_treeview_state()         

    def update_tree_states(self, updated_tasktree):
        for tree_state in self.treeview_state_manager.tree_states:
            try:
                # Try to retrieve the entity this tree state maps to.
                entity = updated_tasktree.get_entity_for_id(tree_state.entity_id)
            except UnregisteredEntityError:
                # The entity the tree state represents no longer exists in the 
                # task data set. Remove the tree state.
                self.treeview_state_manager.remove_tree_state(tree_state.entity_id)
        
    def start_editing(self):
        # Find the editable entity.
        for tree_state in self.treeview_state_manager.tree_states:
            if tree_state.is_editable:
                targeted_entity_id = tree_state.entity_id
                break
        else:
            # Raise an error if no tree states are flagged as editable.
            raise ValueError("Cannot start editing because no tree states are currently flagged as editable.")
        
        # Lookup the tree path mapped to the provided entity ID.
        treepath = self.task_treestore.get_path_for_entity_id(targeted_entity_id)
        
        # Focus on the targeted row and make it editable.
        debug("Setting editable row: {0}.".format(treepath))        
        
        # Store the current treeview change ignore status before ensuring its
        # set to True. Reverting back to the "original" status allows this 
        # process to avoid disrupting the state set by other, surrounding
        # code.
        original_treeview_change_ignored = self.is_treeview_change_ignored
        self.is_treeview_change_ignored = True
        self.view.start_editing_str(treepath)        
        self.is_treeview_change_ignored = original_treeview_change_ignored        
        debug("Finished setting editable row.")

    def set_entity_id_editable(self, entity_id):
        # TODO: Remove debug print.
        debug("Making this entity ID editable: {0}".format(entity_id))
        
        raise NotImplementedError
        
        # Clear the selected and editable flags of all other entities. 
        # This ensures only the targeted editable entity will be highlighted
        # and editable.
        debug("Removing editable and selected from all other tree states.")
        for tree_state in self.treeview_state_manager.tree_states:
            try:
                self.update_tree_state(tree_state.entity_id,
                    is_editable=False, is_selected=False,
                    is_expanded=tree_state.is_expanded)
            except EmptyTreeStateError:
                # This is fine, an empty state has been established but will 
                # be cleaned up in the following prune call.
                pass
            
        # Clean out any "empty" tree states.
        debug("Pruning tree states.")
        self._prune_tree_states()
        
        # Expand all parent tree nodes (Tasks) so that the new editable 
        # entity can be seen and selected.
        editable_entity = self._tasktree.get_entity_for_id(entity_id)
        try:
            next_parent_id = editable_entity.parent_id
            while next_parent_id is not None:
                parent = self._tasktree.get_entity_for_id(next_parent_id)
                
                # Make sure each parent Task is expanded, but not editable or 
                # selected.                
                self.update_tree_state(parent.entity_id,
                    is_editable=False, is_selected=False, is_expanded=True)
                
                # Move up to the next parent Task.
                next_parent_id = parent.parent_id
                
            # All parent tasks have been expanded, now expand the TaskTree.
            self.update_tree_state(editable_entity.tasklist_id,
                is_editable=False, is_selected=False, is_expanded=True)            
        except AttributeError:
            # This indicates the entity is a TaskList, which is fine--it will
            # always be visible by default.
            pass        
                
        # Create a new tree state--or update the existing tree state--for the 
        # entity, marking it as selected and editable.
        self.update_tree_state(entity_id,
                    is_editable=True, is_selected=True,
                    is_expanded=False)
                
        # Update the tree view to reflect the new tree states.
        self.update_treeview_state()
                
        # Request an editing callback (edit the title of the new list).
        self._request_editing_callback() 

    def _get_treepath_for_path(self, path):
        self.task_treestore.get_iter_from_string(path)

#    def _get_parent_entity(self, entity):
#        assert isinstance(entity, Task)
#
#        return None
    
    def has_tasklist_path(self, entity_id):
        # Find the treestore path registered to the entity ID, and split it
        # into its individual branch indices.
        treestore_path = self.task_treestore.get_path_for_entity_id(entity_id)        
        treestore_indices = treestore_path.split(":")
        
        return len(treestore_indices) == 1

    def refresh_treeview_state(self):        
        # Clear out existing tree states.
#        self._clear_tree_state()

        # Collect the existing current state of the tree view.
        self._collect_tree_state()
        
        # TODO: Remove print debug statements.
        debug("Refreshed treeview states:")
        debug(pprint.pformat(self.treeview_state_manager.tree_states, indent=4, width=1))            
        
    def clear_treeview_state(self):
        # Clear existing tree state information.
        self.treeview_state_manager.clear_all_states()       
        
    def clear_treeview_selections(self):
        self.view.get_selection().unselect_all()
    
    def update_view(self, updated_tasktree):      
        # Ensure that there is no response to events that are raised when
        # updating/altering the tree store and view.        
        self.is_treeview_change_ignored = True
                
        # Update the tree view data model (TaskTreeStore).
        self.update_tasktree_model(updated_tasktree)
        
        # Update the tree view to reflect the current updated tree state.
        self.update_treeview_state()
                
        # Enable tree view change event handling.
        self.is_treeview_change_ignored = False

    def collect_treeview_state(self):
        temp_debug("Collecting tree states...")
        
        # Begin collection from the root row/node.
        tree_iter = self.task_treestore.get_iter_first()
        
        self._collect_treeview_state_recurse(tree_iter)
        
    def _collect_treeview_state_recurse(self, tree_iter):
        while tree_iter != None:
            tree_path = self.task_treestore.get_path(tree_iter)

            is_expanded = is_selected = False

            if self.view.row_expanded(tree_path):
                is_expanded = True

            if self.view.get_selection().path_is_selected(tree_path):
                is_selected = True
                
            # TODO: Is there a way to tell if the row is "editing"?
            
            if is_expanded or is_selected:
                entity_id = self.task_treestore[tree_iter][TaskTreeStoreNode.ENTITY_ID]
                entity = self._tasktree.get_entity_for_id(entity_id)
                
                if is_expanded:
                    self.treeview_state_manager.expand_entity(entity)
                
                if is_selected:
                    self.treeview_state_manager.select_entity(entity)

            if self.task_treestore.iter_has_child(tree_iter):
                child_iter = self.task_treestore.iter_children(tree_iter)

                self._collect_treeview_state_recurse(child_iter)

            tree_iter = self.task_treestore.iter_next(tree_iter)

    def update_treeview_state(self):
        # TODO: Remove debug print statements.
        
        debug("Resetting tree view widget.")
        temp_debug("Current tree view states: {0}".format(self.treeview_state_manager))
        # Collapse any tree expansions.
        self.view.collapse_all()
        
        # Clear any existing selections. This must be called after the tree
        # is fully collapsed or selections can survive the refresh.
        self.view.get_selection().unselect_all()
        
        debug("Restoring tree states... (ignoring tree view changes)")
        treeview_change_ignored_original = self.is_treeview_change_ignored
        self.is_treeview_change_ignored = True
        
        # Order tree row states by the depth of the node they target. This 
        # helps fix errors that arise when deeper nodes are expanded before
        # their shallower parent nodes are.
        sorted_tree_states = self._sort_tree_states(self.treeview_state_manager.tree_states)
        
        # Iterate over the tree states, using the flags contained in each to
        # individually update the GUI tree view.        
        for tree_row_state in sorted_tree_states:
            debug("\t restoring: {0}".format(tree_row_state))
            
            """
            TODO: Are these following steps all necessary, or is there a 
            shortcut?
            """
            treestore_path_str = self.task_treestore.get_path_for_entity_id(tree_row_state.entity_id)
            treestore_iter = self.task_treestore.get_iter(treestore_path_str)
            treestore_path = self.task_treestore.get_path(treestore_iter)
            
            if tree_row_state.is_expanded:
                temp_debug("Expanding path: {0} for ID {1}".format(treestore_path, tree_row_state.entity_id))
                # Use expand_to_path rather than expand_path in order to 
                # fix an error where deeper nodes where being expanded before
                # shallower nodes, which caused the deeper nodes to remain
                # hidden.
                self.view.expand_to_path(treestore_path)

            if tree_row_state.is_selected:
                temp_debug("Selecting path: {0} for ID {1}".format(treestore_path, tree_row_state.entity_id))
                self.view.get_selection().select_path(treestore_path)

        debug("Restoring tree view change ignore status to: {0}".format(treeview_change_ignored_original))
        self.is_treeview_change_ignored = treeview_change_ignored_original
        
    def _sort_tree_states(self, tree_states):        
        # Compute the current depth (path "length") for each tree state.
        tree_states_and_depths = list()         
        for tree_row_state in tree_states:
            treestore_path_str = self.task_treestore.get_path_for_entity_id(tree_row_state.entity_id)
            depth = len(treestore_path_str.split(TaskTreeStore.PATH_SEPARATOR))
            
            # Add the tree state and node depth to an intermediate list.
            tree_states_and_depths.append((depth, tree_row_state))
        
        # Sort the temporary list of associated tree states and depths by 
        # depth.        
        sorted_tree_states = [sorted_tree_state[1] for sorted_tree_state 
            in sorted(tree_states_and_depths, key=itemgetter(0))]
        
        return sorted_tree_states
                
    def _handle_cell_edited(self, tree_title_cell, tree_path, updated_title):
        # Find the entity that was edited through the tree view.
        target_entity_id = self.task_treestore.get_entity_id_for_path(tree_path)

        # Fire event, sending along the target entity ID and the
        # updated title text.
        self.entity_title_edited.fire(target_entity_id, updated_title)

    @entryExit()
    def _handle_row_expanded(self, treeview, treeiter, treepath):
        entity_id = self.task_treestore[treeiter][TaskTreeStoreNode.ENTITY_ID]
        entity = self._tasktree.get_entity_for_id(entity_id)
        
        self.treeview_state_manager.expand_entity(entity)

    @entryExit()
    def _handle_row_collapsed(self, treeview, treeiter, treepath):
        entity_id = self.task_treestore[treeiter][TaskTreeStoreNode.ENTITY_ID]
        entity = self._tasktree.get_entity_for_id(entity_id)
        
        self.treeview_state_manager.collapse_entity(entity)
        
    @entryExit()
    def _handle_selection_changed(self, selection_data):
        debug("Handling selection change.")
        
        has_selected_rows = True
        if selection_data.count_selected_rows() == 0:
            has_selected_rows = False
        
        """
        TODO: TaskTreeStore.is_updating_tree and this class' 
        is_treeview_change_ignored properties are probably redundant. I think
        the TaskTreeStore updating prop can be safely removed.
        """
        # If the updating flag is set, or if no rows have been selected, 
        # return immediately to prevent handling spurious selection 
        # change events (fired by Gtk in response to tree model changes?).               
        if (self.task_treestore.is_updating_tree or not has_selected_rows
            or self.is_treeview_change_ignored):       
            return
            
        self.treeview_state_manager.clear_all_selections()
        self.collect_treeview_state()
                       
        # TODO: Remove this debug print statement.
        debug("TreeView state after sel change: {0}".format(self.treeview_state_manager))
                        
        """
        TODO: Make this a bit smarter/more efficient by only firing when the
        selection state actually changes, instead of on every selection 
        event.
        """
        # Notify any listeners of the change in selection state.
        self.selection_state_changed.fire(self.treeview_state_manager.tasklist_selection_state,
            self.treeview_state_manager.task_selection_state)  
#------------------------------------------------------------------------------ 

class TaskTreeViewState(object):
    """
    Very simple convenience class to group the three tree node states
    (is expanded, is selected, is_editable) together.
    """
    def __init__(self, entity, is_expanded=None,
        is_selected=None, is_editable=None):
        self.entity = entity
        self.is_expanded = is_expanded
        self.is_selected = is_selected
        self.is_editable = is_editable
    
    @property
    def entity_id(self):
        return self.entity.entity_id

    def __str__(self):
        info_str = "<id: {id}; expnd: {expanded}; slctd: {selected}; edit: {editable}>"
        info_str = info_str.format(expanded=self.is_expanded,
             selected=self.is_selected,
            editable=self.is_editable, id=self.entity_id)
        
        return info_str
    
    def __repr__(self):
        return self.__str__()
#------------------------------------------------------------------------------ 
        
class EmptyTreeStateError(ValueError):
    """Simple error type indicator/marker class."""
    def __init__(self, *args, **kwargs):
        ValueError.__init__(self, *args, **kwargs)
#------------------------------------------------------------------------------

class TreeStateEditableError(ValueError):
    """Simple error type indicator/marker class."""
    def __init__(self, message):
        ValueError.__init__(self, message)
#------------------------------------------------------------------------------ 

class TaskTreeViewStateManager(object):
    def __init__(self):
        # Clearing all states will also initialize the state containing 
        # properties.
        self.clear_all_states() 

    @property
    def selected_entities(self):
        return [state.entity for state in self.tree_states if state.is_selected]
    
    @property
    def selected_tasklists(self):
        return [entity for entity in self.selected_entities
                if not self._is_entity_task(entity)]
    
    @property
    def selected_tasks(self):
        return [entity for entity in self.selected_entities
                if self._is_entity_task(entity)]  
        
    @property
    def tasklist_selection_state(self):
        if len(self.selected_tasklists) == 1:
            return TaskTreeSelectionState.SINGLE
        elif len(self.selected_tasklists) > 1:
            return TaskTreeSelectionState.MULTIPLE_HETEROGENOUS
        
        return TaskTreeSelectionState.NONE
    
    @property
    def task_selection_state(self):
        if len(self.selected_tasks) == 1:
            return TaskTreeSelectionState.SINGLE
        elif len(self.selected_tasks) > 1:
            # Determine if all selected tasks belong to the same tasklist or
            # not.
            is_homogenous = True
            prev_tasklist_id = None
            
            for selected_task in self.selected_tasks:
                if prev_tasklist_id is not None and selected_task.tasklist_id != prev_tasklist_id:
                    is_homogenous = False
                    break
                else:
                    prev_tasklist_id = selected_task.tasklist_id

            if is_homogenous:
                return TaskTreeSelectionState.MULTIPLE_HOMOGENOUS
            else:
                return TaskTreeSelectionState.MULTIPLE_HETEROGENOUS
        
        return TaskTreeSelectionState.NONE
    
    @property
    def tree_states(self):
        return self._tree_states.values()
    
    def _clear_tree_states(self):
        self._tree_states = dict()
        
    def _is_entity_task(self, entity):
        return hasattr(entity, "parent_id") and hasattr(entity, "tasklist_id")

    def _is_tree_state_valid(self, tree_state):
        try:
            self._validate_tree_state(tree_state)
            return True
        except:
            # Catch everything?
            return False

    def _prune_tree_states(self):
        # Remove any tree states that have no state status flags set.
        self._tree_states = {state.entity_id: state for state 
                            in self.tree_states 
                            if self._is_tree_state_valid(state)}
        
        # Ensure at most one entity/tree state is set to editable.
        editable_count = 0
        editable_tree_state = None
        for tree_state in self.tree_states:
            if tree_state.is_editable:
                editable_count += 1
            
                if editable_count > 1:
                    raise TreeStateEditableError("Only one tree state can be flagged editable at once; at least two currently are: {0} and {1}".format(editable_tree_state, tree_state))
                else:
                    editable_tree_state = tree_state
    
    def _validate_tree_state(self, tree_state):
        """
        TODO: Eventually this should throw a more descriptive error that
        mentions that the tree state is mapped to an unregistered entity.
        """
        
        # If a tree state is editable, is must also be flagged selected.        
        if tree_state.is_editable and not tree_state.is_selected:
            raise ValueError("Tree state for entity ID '{id}' is editable, but is not also flagged selected.".format(id=tree_state.entity_id))
        
        if not (tree_state.is_expanded or tree_state.is_selected 
            or tree_state.is_editable):
            raise EmptyTreeStateError("Tree state has no flags enabled.")
        
        return True
    
    def collapse_entity(self, entity):
        self.update_tree_state(entity, is_expanded=False)        
    
    def clear_all_states(self):
        self._clear_tree_states()
    
    def clear_all_selections(self):
        self.update_all_tree_states(is_selected=False)
    
    def clear_editable(self, target_entity):
        # Clear the editable tree state for the target entity.
        try:
            self.update_tree_state(target_entity, is_editable=False)
        except EmptyTreeStateError:
            # This is ok, it just means the tree state ended up empty 
            # (entity is no longer selected).
            pass
        
    def has_editable_entity(self):
        for tree_state in self.tree_states:
            if tree_state.is_editable:
                return True
        else:
            return False
    
    def remove_tree_state(self, tree_state_entity_id):
        # Don't wrap this in a try/except block to allow the potential 
        # KeyError to bubble up.
        del self._tree_states[tree_state_entity_id]
    
    def set_entity_editable(self, entity):
        # Clear the editable and selected flags from all other entities. This
        # ensures the targeted entity will be the only tree row with focus.
        self.update_all_tree_states(is_editable=False, is_selected=False)
        
        # Update the targeted entity, ensuring it's both editable and selected.
        self.update_tree_state(entity, is_editable=True, is_selected=True)            
        
    def update_tree_state(self, entity, is_editable=None, is_selected=None, is_expanded=None):
        # Check to see if the entity ID already has an associated state. 
        # If so, preserve that.
        try:
            # A tree state already exists. Update it instead of 
            # replacing it with a new one.
            tree_state = self._tree_states[entity.entity_id]
        except KeyError:
            # No existing tree state.
            tree_state = TaskTreeViewState(entity)
            
        if is_editable is not None:
            tree_state.is_editable = is_editable
            
        if is_expanded is not None:
            tree_state.is_expanded = is_expanded
            
        if is_selected is not None:
            tree_state.is_selected = is_selected
            
        try:
            self._validate_tree_state(tree_state)        
            
            # TODO: Remove debug print.
            debug("Updating tree state: {0}".format(tree_state))
        
            self._tree_states[entity.entity_id] = tree_state
        except EmptyTreeStateError:
            # Tree state has been cleared of all flags, so it can be 
            # removed from the collection.
            debug("Removing empty tree state for entity {id}.".format(id=entity.entity_id))
            
            del self._tree_states[entity.entity_id]       

        """
        TODO: Is this call really necessary, especially now that empty 
        TreeStates are actively being removed?
        """
        self._prune_tree_states()
        
    def update_all_tree_states(self, is_editable=None, is_selected=None, is_expanded=None):
        """Update all tree state records with the provided flags.
        
        Flags that aren't provided as arguments are left as-is in 
        each individual tree state.
        """
        for tree_state in self.tree_states:
            try:
                self.update_tree_state(tree_state.entity,
                    is_editable=is_editable, is_selected=is_selected,
                    is_expanded=is_expanded)
            except EmptyTreeStateError:
                # That's fine, empty state will get cleaned up afterwards.
                pass
            
        # Clear away any empty tree states.
        self._prune_tree_states()
    
    def expand_entity(self, entity):        
        self.update_tree_state(entity, is_expanded=True)
    
    def select_entity(self, entity):
        self.update_tree_state(entity, is_selected=True)
        
    def __str__(self):
        info_str = "<TTVSM - tasklist sel. st.: {tasklist_state}; task sel. st.: {task_state}; sel. entities: {selected_entities}>"
        info_str = info_str.format(tasklist_state=self.tasklist_selection_state, task_state=self.task_selection_state, selected_entities=self.selected_entities)
        
        states_str = "\nAll tree view states:\n{0}".format(pprint.pformat(self.tree_states, indent=4, width=1))
         
        return info_str + states_str 
#------------------------------------------------------------------------------

class TaskTreeSelectionState(object):
    NONE = "none"
    SINGLE = "single"
    # All selections are in the same TaskList.
    MULTIPLE_HOMOGENOUS = "multiple_homogenous" 
    # Selections are spread across multiple TaskLists.
    MULTIPLE_HETEROGENOUS = "multiple_heterogenous"
#------------------------------------------------------------------------------ 

class TaskTreeView(Gtk.TreeView):
    def __init__(self):
        Gtk.TreeView.__init__(self)

        # An editable text cell for the task/tasklist title.
        self.title_renderer = Gtk.CellRendererText()
        self.title_renderer.set_property("wrap-width", 200)
        self.title_renderer.set_property("editable", True)

        # An icon cell for the node icon. These reflect type (tasklist vs task)
        # and status (task complete vs incomplete).
        self.image_renderer = Gtk.CellRendererPixbuf()

        self.icon_title_column = Gtk.TreeViewColumn("Task Name")
        self.icon_title_column.pack_start(self.image_renderer, False)
        self.icon_title_column.pack_end(self.title_renderer, True)
        self.icon_title_column.add_attribute(self.image_renderer, "pixbuf", TaskTreeStoreNode.ICON)
        self.icon_title_column.add_attribute(self.title_renderer, "text", TaskTreeStoreNode.LABEL)
        self.append_column(self.icon_title_column)

        # Set the selection mode to allow multiple nodes to be selected
        # simultaneously.
        self.get_selection().set_mode(Gtk.SelectionMode.MULTIPLE)

        # Set the scrolling property???
        self.set_vscroll_policy(Gtk.ScrollablePolicy.NATURAL)
        self.set_hscroll_policy(Gtk.ScrollablePolicy.NATURAL)
        
    def clear_selection(self):
        self.get_selection().unselect_all()
        
    def start_editing_str(self, treepath_str):
        treestore_iter = self.get_model().get_iter(treepath_str)
        treestore_path = self.get_model().get_path(treestore_iter)
        self.start_editing(treestore_path)

    def start_editing(self, treepath):
        """
        TODO: Fix these comments; most likely the expansion of parent tree
        nodes will happen elsewhere (as it needs to be reflected in tree state
        information).
        """
        # This will need to expand any collapsed parent nodes
        # in order to get the selection properly set. Otherwise, by default the 
        # new node could be hidden.
        debug("Setting tree path '{0}' editable".format(treepath))
        
        # This call shouldn't be necessary, as the proper set of tree states,
        # when applied through the (preceding) restore tree view state 
        # process, should have already expanded the full path to the targeted
        # node.
        self.expand_to_path(treepath)
        
        self.get_selection().select_path(treepath.to_string())
        self.scroll_to_cell(treepath.to_string())
        self.set_cursor_on_cell(treepath, self.icon_title_column, self.title_renderer, start_editing=True)
#------------------------------------------------------------------------------ 

class BinaryIconButton(Gtk.Button):
    def __init__(self, click_event_name, icon_file_path,
        disabled_icon_file_path=None, is_enabled=True):
        Gtk.Button.__init__(self)

        self.click_event_name = click_event_name
        self.enabled_icon_file_path = icon_file_path

        if disabled_icon_file_path is None:
            # If there is no specified disabled icon file path, assume that the
            # file can be found in this location:
            # [enabled icon path]-disabled[enabled-icon-extension]
            file_ext_location = self.enabled_icon_file_path.rindex('.')
            icon_file_root = self.enabled_icon_file_path[0:file_ext_location]
            icon_file_ext = self.enabled_icon_file_path[file_ext_location:len(self.enabled_icon_file_path)]
            disabled_icon_file_path = icon_file_root + "_disabled" + icon_file_ext
        self.disabled_icon_file_path = disabled_icon_file_path

        # Load the icon images.
        self.icon_image = Gtk.Image()
        self.add(self.icon_image)

        # Set the initial enabled state.
        self.is_enabled = is_enabled

        # Set the appropriate icon.
        if self.is_enabled:
            self.enable()
        else:
            self.disable()

        # Connect the click event to a EventRegistry notifier.
        self.connect("clicked",
            EventRegistry.create_notifier_callback(self.click_event_name))
        
    def _set_icon(self):
        # Add the Image that reflects the current button state.
        if self.is_enabled:
            self.icon_image.set_from_file(self.enabled_icon_file_path)
        else:
            self.icon_image.set_from_file(self.disabled_icon_file_path)

    def enable(self):
        self.is_enabled = True
        self._set_icon()
        self.set_sensitive(True)

    def disable(self):
        self.is_enabled = False
        self._set_icon()
        self.set_sensitive(False)

    def set_state(self, is_enabled):
        if is_enabled:
            self.enable()
        else:
            self.disable()
#------------------------------------------------------------------------------ 
