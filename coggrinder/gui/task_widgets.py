"""
Created on Mar 29, 2012

@author: Clay Carpenter
"""
from gi.repository import Gtk, GdkPixbuf
from coggrinder.entities.tasks import TaskList, Task
from coggrinder.resources.icons import buttons
from coggrinder.gui.events import Event
from coggrinder.gui.task_treestore import TaskTreeStore, TreeNode


class TaskTreeWindowController(object):
    def __init__(self, tasktree_service=None):                
        self.tasktree = None
        
        self._tasktree_service = tasktree_service
        
        # Initialize the TaskTreeWindow Gtk window that serves as the view
        # for this controller.
        self.view = TaskTreeWindow()
        
        # Wire up all of the view events to handler methods in this controller.
        self._wire_events()
        
    def _wire_events(self):
        # Connect to all events that need to be listened for.
        self.view.save_button_clicked.register(self._handle_save_event)
        self.view.sync_button_clicked.register(self._handle_sync_event)
        self.view.revert_button_clicked.register(self._handle_revert_event)
        
        self.view.add_list_button_clicked.register(self._handle_add_list_event)
        self.view.remove_list_button_clicked.register(self._handle_remove_list_event)
        
        self.view.add_task_button_clicked.register(self._handle_add_task_event)
        self.view.edit_task_button_clicked.register(self._handle_edit_task_event)
        self.view.complete_task_button_clicked.register(self._handle_complete_task_event)
        self.view.remove_task_button_clicked.register(self._handle_remove_task_event)
        
        self.view.promote_task_button_clicked.register(self._handle_promote_task_event)
        self.view.demote_task_button_clicked.register(self._handle_demote_task_event)
        self.view.reorder_task_up_button_clicked.register(self._handle_reorder_task_up_event)
        self.view.reorder_task_down_button_clicked.register(self._handle_reorder_task_down_event)
                
        self.view.configure_button_clicked.register(self._handle_configure_event)
        
        self.view.entity_title_edited.register(self._handle_entity_title_updated)

    def refresh_task_data(self):
        """
        Pull updated tasklist and task information from the task tree
        services Store the updated results locally before refreshing the UI
        task tree.
        """
        # Pull updated task data (tasklists and tasks) from the services.
        self._tasktree_service.refresh_tasktree()
                
        # Update the UI task tree.
        self.view.update_tasktree(self._tasktree_service.tree)

    def _handle_save_event(self, button):
        raise NotImplementedError
    
    def _handle_sync_event(self, button):        
        self.refresh_task_data()
    
    def _handle_revert_event(self, button):
        raise NotImplementedError
    
    def _handle_add_list_event(self, button):
        # Create the new (blank) tasklist, and add it to the task tree.
        new_tasklist = self.tasklist_service.add_tasklist(TaskList(title=""))
        self.refresh_task_data()
        
        # Find the new tasklist, select it (wiping out other selections), and
        # set it to editable/editing.
        self.view.set_entity_editable(new_tasklist)
    
    def _handle_remove_list_event(self, button):
        # Locate the selected tasklist.
        selected_entities = self.view.get_selected_entities()
        assert len(selected_entities) == 1, "Should only allow a single tasklist to be selected for deletion."
        tasklist = selected_entities[0]
        
        # Delete the tasklist.
        self.tasklist_service.delete_tasklist(tasklist)
        
        # Refresh the task data, tree.
        self.refresh_task_data()
        
    def _handle_add_task_event(self, button):
        # Find selected entity. This will determine the new tasks's parent 
        # tasklist and, optionally, it's parent new_task as well.
        selected_entities = self.view.get_selected_entities()
        assert len(selected_entities) == 1, "Should only allow a single tasklist or new_task to be selected for as a parent for the new new_task."
        parent = selected_entities[0]
        
        if isinstance(parent, TaskList):
            # Get the tasklist id.
            tasklist_id = parent.entity_id
            parent_id = None
        elif isinstance(parent, Task):
            # Get the tasklist id.
            tasklist_id = parent.tasklist_id
            parent_id = parent.entity_id
        
        # Create an empty new task with only the parent ID and tasklist ID 
        # specified.
        new_task = Task(parent_id=parent_id, tasklist_id=tasklist_id)
            
        # Add the new task.
        new_task = self.task_service.add_task(new_task)
        
        # Refresh the task data, tree.
        self.refresh_task_data()
        
        # Override existing selection. Select new task and set the tree node 
        # to be "editable". This will need to expand any collapsed parent nodes
        # in order to get the selection properly set. Otherwise, by default the 
        # new node could be hidden.
        self.view.set_entity_editable(new_task)        
        
    def _handle_edit_task_event(self, button):
        raise NotImplementedError
        
    def _handle_complete_task_event(self, button):
        raise NotImplementedError
        
    def _handle_remove_task_event(self, button):
        # Locate the selected task or tasks.
        selected_entities = self.view.get_selected_entities()
        assert len(selected_entities) > 0
        
        # Collect all of the selected entities that are tasks.
        selected_tasks = list()
        for selected_entity in selected_entities:
            if isinstance(selected_entity, Task):
                selected_tasks.append(selected_entity)
        assert len(selected_tasks) > 0
        
        # TODO: Should this code be moved to the services layer? I think so.
        
        # For each task, delete the task. Promote any children of the task to 
        # be children of the task's parent (task or tasklist).
        # Keep track of the child tasks that have their parent updated, as 
        # they will need 
        update_tasks = dict()
        for selected_task in selected_tasks:
            # Remove the selected task from the local tasks dict, and from the 
            # update-pending tasks list, if it's present there.
            assert self._tasks.has_key(selected_task.entity_id)
            del self._tasks[selected_task.entity_id]
            if update_tasks.has_key(selected_task.entity_id):
                del update_tasks[selected_task.entity_id]
            
            child_tasks = self._find_child_tasks(selected_task)
            
            for child_task in child_tasks:
                # If the selected task has another task as a parent, then 
                # this will move the child task up to be a child task of the 
                # selected task's parent. Otherwise, the child task will 
                # receive a None value from the selected task's parent ID
                # and will be moved up to a top-level task (direct child of the
                # tasklist).
                child_task.parent_id = selected_task.parent_id
                
                # Include the child task in the list of tasks to be updated.
                update_tasks[child_task.entity_id] = child_task
        
        # Execute the updates.
        for update_task_id in update_tasks:
            # TODO: This needs to be a move operation, not a parent operation.
            # According to the Google Tasks service docs, it doesn't look like
            # this operation has much chance of succeeding without adding
            # a concept of ordering locally and sending that information along
            # with the move operation request.
            self.task_service.update_task(update_tasks[update_task_id])
            
        # Execute the deletions.
        for deleted_task in selected_tasks:
            self.task_service.delete_task(deleted_task)

        # Refresh the data from the server and update the UI.
        self.refresh_task_data()
        
    def _handle_promote_task_event(self, button):
        raise NotImplementedError
        
    def _handle_demote_task_event(self, button):
        raise NotImplementedError
        
    def _handle_reorder_task_up_event(self, button):
        raise NotImplementedError
        
    def _handle_reorder_task_down_event(self, button):
        raise NotImplementedError
    
    def _handle_configure_event(self, button):
        raise NotImplementedError
        
    def _handle_entity_title_updated(self, target_entity, updated_title):
        assert (target_entity is not None and target_entity.entity_id is not None)
        
        # Set the entity's updated title.
        target_entity.title = updated_title
        
        # Determine the entity type (task or tasklist).
        if isinstance(target_entity, TaskList):            
            # Send the updated tasklist to the server.
            target_entity = self.tasklist_service.update_tasklist(target_entity)
        elif isinstance(target_entity, Task):     
            # Send the updated task to the server.
            target_entity = self.task_service.update_task(target_entity)
        else:
            raise ValueError("Target entity must be of type TaskList or Task, was instead {0}".format(type(target_entity)))
        
        # Update the local task data.
        self.refresh_task_data()

    def _find_child_tasks(self, parent_task):
        """
        Retrieve an unordered list of all child tasks belonging to the 
        specified parent task.
        
        Will always return a list object, even if no children are found.
        """
        assert (parent_task is not None 
            and parent_task.tasklist_id is not None
            and isinstance(parent_task, Task))
        
        # Simple unordered list of child tasks.
        child_tasks = list()
        
        for task_id in self._tasks:
            # Look for tasks with a parent ID that matches the parent task's
            # ID and belonging to the same tasklist as the parent task.
            task = self._tasks[task_id]
            if (task.tasklist_id == parent_task.tasklist_id 
                and task.parent_id == parent_task.entity_id):
                # Found a child of the parent task, add it to the list.
                child_tasks.append(task)
                
        return child_tasks

    def show(self):
        self.view.show_all()
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
        
        # Propagate toolbar events.
        # TODO: Fix all of this redundant/boilerplate code.
        self.save_button_clicked = Event.propagate(
            self.toolbar_controller.save_button_clicked)
        self.sync_button_clicked = Event.propagate(
            self.toolbar_controller.sync_button_clicked)
        self.revert_button_clicked = Event.propagate(
            self.toolbar_controller.revert_button_clicked)
                
        self.add_list_button_clicked = Event.propagate(
            self.toolbar_controller.add_list_button_clicked)
        self.remove_list_button_clicked = Event.propagate(
            self.toolbar_controller.remove_list_button_clicked)
                
        self.add_task_button_clicked = Event.propagate(
            self.toolbar_controller.add_task_button_clicked)       
        self.edit_task_button_clicked = Event.propagate(
            self.toolbar_controller.edit_task_button_clicked)       
        self.complete_task_button_clicked = Event.propagate(
            self.toolbar_controller.complete_task_button_clicked)       
        self.remove_task_button_clicked = Event.propagate(
            self.toolbar_controller.remove_task_button_clicked)
        
        self.promote_task_button_clicked = Event.propagate(
            self.toolbar_controller.promote_task_button_clicked)
        self.demote_task_button_clicked = Event.propagate(
            self.toolbar_controller.demote_task_button_clicked)
        self.reorder_task_up_button_clicked = Event.propagate(
            self.toolbar_controller.reorder_task_up_button_clicked)
        self.reorder_task_down_button_clicked = Event.propagate(
            self.toolbar_controller.reorder_task_down_button_clicked)
                
        self.configure_button_clicked = Event.propagate(
            self.toolbar_controller.configure_button_clicked)
        
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
        
    def update_tasktree(self, tasktree):
        self.treeview_controller.update_tasktree(tasktree)
        
    def set_entity_editable(self, target_entity):
        """
        Finds the target entity within the task tree and bring
        the user's focus to the row while making the entity title editable.
        If the entity is not a tasklist (top-level in tree and always visible), 
        any parent nodes will also be expanded as necessary in order to make
        the target entity visible.  
        """
        self.treeview_controller.set_entity_editable(target_entity)
        
    def get_selected_entities(self):
        return self.treeview_controller.get_selected_entities()
#------------------------------------------------------------------------------ 

class TaskToolbarViewController(object):
    """
    Listens for selection change events, and sends this information to the 
    view.
    
    Converts UI button events into domain events.
    """
    def __init__(self):
        self.view = TaskToolbarView()
        
        # Register toolbar button Events and wire them to the Gtk event system
        # for the actual button widgets.
        # TODO: Fix redundant/boilerplate event declaration code.
        self.save_button_clicked = Event()
        self.view.save_button.connect("clicked",
            self.save_button_clicked.fire)        
        self.sync_button_clicked = Event()
        self.view.sync_button.connect("clicked",
            self.sync_button_clicked.fire)        
        self.revert_button_clicked = Event()
        self.view.revert_button.connect("clicked",
            self.revert_button_clicked.fire)
                
        self.add_list_button_clicked = Event()
        self.view.add_list_button.connect("clicked",
            self.add_list_button_clicked.fire)        
        self.remove_list_button_clicked = Event()
        self.view.remove_list_button.connect("clicked",
            self.remove_list_button_clicked.fire)
                
        self.add_task_button_clicked = Event()
        self.view.add_task_button.connect("clicked",
            self.add_task_button_clicked.fire) 
        self.edit_task_button_clicked = Event()
        self.view.edit_task_button.connect("clicked",
            self.edit_task_button_clicked.fire) 
        self.complete_task_button_clicked = Event()
        self.view.complete_task_button.connect("clicked",
            self.complete_task_button_clicked.fire) 
        self.remove_task_button_clicked = Event()
        self.view.remove_task_button.connect("clicked",
            self.remove_task_button_clicked.fire)
         
        self.promote_task_button_clicked = Event()
        self.view.promote_task_button.connect("clicked",
            self.promote_task_button_clicked.fire)
        self.demote_task_button_clicked = Event()
        self.view.demote_task_button.connect("clicked",
            self.demote_task_button_clicked.fire)
        self.reorder_task_up_button_clicked = Event()
        self.view.reorder_task_up_button.connect("clicked",
            self.reorder_task_up_button_clicked.fire)
        self.reorder_task_down_button_clicked = Event()
        self.view.reorder_task_down_button.connect("clicked",
            self.reorder_task_down_button_clicked.fire)
        
        self.configure_button_clicked = Event()
        self.view.configure_button.connect("clicked",
            self.configure_button_clicked.fire)      
        
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
        
        self.save_button = BinaryIconButton(buttons.FILES["save.png"], is_enabled=False)
        button_box.add(self.save_button)
        
        self.sync_button = BinaryIconButton(buttons.FILES["sync.png"])
        button_box.add(self.sync_button)
        
        self.revert_button = BinaryIconButton(buttons.FILES["revert.png"], is_enabled=False)
        button_box.add(self.revert_button)
        
        return button_box
    
    def _build_list_buttons(self):
        """
        Builds buttons for:
        -- Add new list
        -- Delete existing list
        """
        button_box = Gtk.HBox(spacing=5)
        
        self.add_list_button = BinaryIconButton(buttons.FILES["folder_plus.png"])
        button_box.add(self.add_list_button)
        
        self.remove_list_button = BinaryIconButton(buttons.FILES["folder_delete.png"], is_enabled=False)
        button_box.add(self.remove_list_button)
        
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
        
        self.add_task_button = BinaryIconButton(buttons.FILES["doc_plus.png"], is_enabled=False)
        button_box.add(self.add_task_button)
        
        self.edit_task_button = BinaryIconButton(buttons.FILES["doc_edit.png"], is_enabled=False)
        button_box.add(self.edit_task_button)
        
        self.complete_task_button = BinaryIconButton(buttons.FILES["checkbox_checked.png"], is_enabled=False)
        button_box.add(self.complete_task_button)
        
        self.remove_task_button = BinaryIconButton(buttons.FILES["doc_delete.png"], is_enabled=False)
        button_box.add(self.remove_task_button)
        
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
        
        self.promote_task_button = BinaryIconButton(buttons.FILES["sq_br_prev.png"], is_enabled=False)
        button_box.add(self.promote_task_button)
        
        self.demote_task_button = BinaryIconButton(buttons.FILES["sq_br_next.png"], is_enabled=False)
        button_box.add(self.demote_task_button)
        
        self.reorder_task_up_button = BinaryIconButton(buttons.FILES["sq_br_up.png"], is_enabled=False)
        button_box.add(self.reorder_task_up_button)
        
        self.reorder_task_down_button = BinaryIconButton(buttons.FILES["sq_br_down.png"], is_enabled=False)
        button_box.add(self.reorder_task_down_button)
        
        return button_box
    
    def _build_configuration_buttons(self):
        """
        Builds buttons for:
        -- Configure program options
        """
        button_box = Gtk.HBox(spacing=5)
        
        self.configure_button = BinaryIconButton(buttons.FILES["cog.png"])
        button_box.add(self.configure_button)
        
        return button_box
            
    """
    This would be hard to move to the toolbar view because it requires 
    checking the selection state of the TaskTreeView.
    """
    def update_button_states(self, tasklist_selection_state, task_selection_state):
        # Only enable when single tasklist is selected.
        self.remove_list_button.set_state(tasklist_selection_state == TaskTreeViewController.SelectionState.SINGLE)
                
        # Only show add task when a single row/entity--either task or 
        # tasklist--is selected:
        # -- Task single and tasklist none or
        # -- Task none and tasklist single
        add_task_button_enabled = False
        if (task_selection_state == TaskTreeViewController.SelectionState.SINGLE and tasklist_selection_state == TaskTreeViewController.SelectionState.NONE) or (task_selection_state == TaskTreeViewController.SelectionState.NONE and tasklist_selection_state == TaskTreeViewController.SelectionState.SINGLE):
            add_task_button_enabled = True            
        self.add_task_button.set_state(add_task_button_enabled)
        
        # Show whenever task or tasks are selected, regardless of tasklist.
        task_detail_buttons_enabled = False
        if task_selection_state != TaskTreeViewController.SelectionState.NONE:
            task_detail_buttons_enabled = True
        self.edit_task_button.set_state(task_detail_buttons_enabled)
        self.complete_task_button.set_state(task_detail_buttons_enabled)        
        self.remove_task_button.set_state(task_detail_buttons_enabled)
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
    def __init__(self):
        self.view = TaskTreeView()
        
        # TODO: Connect edited and (selection) changed event handlers.
        self.view.title_renderer.connect("edited", self._handle_cell_edited)
                
        # Monitor selection change events.
        self.view.get_selection().connect("changed",
            self._handle_selection_changed)
        
        # Declare the selection changed and title edited events.
        self.selection_state_changed = Event()
        self.entity_title_edited = Event()
        
        # Establish the tree store (model) that holds the task entity 
        # information.
        self.task_treestore = TaskTreeStore()
        
        # This index allows us to quickly look up where in the tree a given
        # entity is.
        self.entity_path_index = dict()
        
        # TODO: Document the expected keys and values for this dict; how it
        # will be used.
        self.tree_states = dict()
        
        # Set default for clearing flag. This flag is used to help ignore 
        # "system" selection change events that seem to occur during the 
        # Gtk.TreeStore.clear() operation.
        self._is_clearing = False
        
        # Connect the tree store/row_data to the tree view.
        self.view.set_model(self.task_treestore)
        
    def update_tasktree(self, tasktree):
        """Collect the current tree state, replace the tree model, and then 
        restore the tree state (as much as possible).
        """
        
        # Collect current tree state.
        self._rebuild_tree_state()
        
        # Clear out tree. Set clearing flag to disable selection change 
        # handling, as the clear operation will fire those events.
        self._is_clearing = True
        self.task_treestore.clear()
        self._is_clearing = False
        
        # Build a new tree with the updated task data.
        self._tasktree = tasktree
        self.entity_path_index = self.task_treestore.build_tree(tasktree)
        
        # With the new tree structure in place, try to restore the old tree 
        # state to the fullest extent possible.
        self._restore_tree_state()
    
#    def select_entity(self, target_entity):
#        entity_tree_path = self._get_path_for_entity_id(target_entity.entity_id)
#        assert entity_tree_path is not None
#        
#        # TODO: Should the controller really be digging this deep into the 
#        # view, or should the view provide an interface that includes a 
#        # select_path method?
#        self.view.get_selection().select_path(entity_tree_path)
    
    def set_entity_editable(self, entity, is_editable=True):
        # Find the entity within the task tree.        
        entity_tree_path = self._get_path_for_entity_id(entity.entity_id)
        assert entity_tree_path is not None
                
        # Expand any parent nodes of the entity (to ensure it's visible). This 
        # will only be relevant for task entities, as tasklist entities will 
        # always already be visible.
        tree_iter = self.task_treestore.get_iter_from_string(entity_tree_path)
        treepath = self.task_treestore.get_path(tree_iter)
        self.view.expand_to_path(treepath)        
        
        # Select the entity, making the title editable and holding the keyboard
        # focus.        
        treepath = self.task_treestore.get_path(tree_iter)
        self.view.start_editing(treepath)
    
    def _get_treepath_for_path(self, path):
        self.task_treestore.get_iter_from_string(path)
    
    def _get_parent_entity(self, entity):
        assert isinstance(entity, Task)
        
        return None
    
#    def _set_entity_expanded(self, entity, is_expanded=True):
#        # Find the entity within the task tree.
#        entity_tree_path = self._get_path_for_entity_id(entity.entity_id)
#        assert entity_tree_path is not None
#
#        # Expand or collapse the entity.
#        if is_expanded:
        
    def get_selected_entities(self):
        assert (not self._tasklist_selection_state == self.SelectionState.NONE or not self._task_selection_state == self.SelectionState.NONE)
        
        # Ensure tree state information is up to date.
        self._rebuild_tree_state()
                
        # Loop through the tree states, looking for selected entity IDs.
        selected_entities = list()
        for entity_id in self.tree_states.keys():
            tree_state = self.tree_states.get(entity_id)
            
            if tree_state.is_selected:
                if self._tasklists.has_key(entity_id):
                    entity = self._tasklists.get(entity_id)                    
                elif self._tasks.has_key(entity_id):
                    entity = self._tasks.get(entity_id)
                else:
                    raise ValueError("Entity with ID of {0} is not a required type (TaskList or Task)")
                selected_entities.append(entity)
        
        return selected_entities
    
    def _rebuild_tree_state(self):            
        # Clear out existing tree states.
        self.tree_states.clear()
        
        self._collect_tree_state()
        
    def _collect_tree_state(self, tree_iter=None):
        if tree_iter is None:
            # Assume a default position of the root node if nothing has been
            # specified. This allows the method to be called without arguments.
            tree_iter = self.task_treestore.get_iter_first()
            
        while tree_iter != None:
            tree_path = self.task_treestore.get_path(tree_iter)
            
            is_expanded = is_selected = False
            
            if self.view.row_expanded(tree_path):
                is_expanded = True
            
            if self.view.get_selection().path_is_selected(tree_path):
                is_selected = True
            
            if is_expanded or is_selected:
                entity_id = self.task_treestore[tree_iter][TreeNode.ENTITY_ID]

                self.tree_states[entity_id] = self.TreeState(is_expanded, is_selected)            
            
            if self.task_treestore.iter_has_child(tree_iter):
                child_iter = self.task_treestore.iter_children(tree_iter)
                
                self._collect_tree_state(child_iter)
            
            tree_iter = self.task_treestore.iter_next(tree_iter)
    
    def _restore_tree_state(self, tree_iter=None):
        if tree_iter is None:
            # Assume a default position of the root node if nothing has been
            # specified. This allows the method to be called without arguments.
            tree_iter = self.task_treestore.get_iter_first()
            
        while tree_iter != None:
            tree_path = self.task_treestore.get_path(tree_iter)
            current_entity_id = self.task_treestore[tree_iter][TreeNode.ENTITY_ID]
            
            if self.tree_states.has_key(current_entity_id):
                tree_row_state = self.tree_states[current_entity_id]
                
                if tree_row_state.is_expanded:
                    self.view.expand_row(tree_path, False)
                    
                if tree_row_state.is_selected:
                    self.view.get_selection().select_path(tree_path)
            
            if self.task_treestore.iter_has_child(tree_iter):
                child_iter = self.task_treestore.iter_children(tree_iter)
                
                self._restore_tree_state(child_iter)
            
            tree_iter = self.task_treestore.iter_next(tree_iter)
            
    def _get_entity_id_for_path(self, tree_path):
        if tree_path in self.entity_path_index.values():
            key_index = self.entity_path_index.values().index(tree_path)
            return self.entity_path_index.keys()[key_index]
        else:
            raise ValueError(
                "Could not find an entity registered with path {0}".format(
                tree_path))
    
    def _get_path_for_entity_id(self, entity_id):
        if self.entity_path_index.has_key(entity_id):
            return self.entity_path_index.get(entity_id)
        else:
            raise ValueError(
                "Could not find a path for entity with id {0}".format(
                entity_id))
        
    def _get_entity_for_path(self, tree_path):
        entity_id = self._get_entity_id_for_path(tree_path)
        
        if self._tasklists.has_key(entity_id):
            entity = self._tasklists.get(entity_id)
        elif self._tasks.has_key(entity_id):
            entity = self._tasks.get(entity_id)
        else:
            raise ValueError(
                "Could not find an entity for the path {0} and entity id {1}".format(
                tree_path, entity_id))

        return entity
        
    def _handle_cell_edited(self, tree_title_cell, tree_path, updated_title):
        # Find the entity that was edited through the tree view.
        target_entity = self._get_entity_for_path(tree_path)
        assert target_entity is not None
        
        # Fire event, sending along the (unmodified) target entity and the
        # updated title text.
        self.entity_title_edited.fire(target_entity, updated_title)
    
    def _handle_selection_changed(self, selection_data):
        # If the clearing flag is set, return immediately to prevent handling
        # spurious selection change events.
        if self._is_clearing:
            return
        
        selected_rows = selection_data.get_selected_rows()[1]
                
        self._selected_tasks = list()
        self._selected_tasklists = list()
                
        # Count the tasklists and tasks in the selection.
        for new_selected_row in selected_rows:            
            selected_entity = self._get_entity_for_path(
                new_selected_row.to_string())

            if isinstance(selected_entity, TaskList):
                # This row represents a Tasklist.
                self._selected_tasklists.append(selected_entity)
            elif isinstance(selected_entity, Task):
                # This row represents a Task.
                self._selected_tasks.append(selected_entity)
        
        if len(self._selected_tasklists) == 1:
            self._tasklist_selection_state = TaskTreeViewController.SelectionState.SINGLE
        elif len(self._selected_tasklists) > 1:
            self._tasklist_selection_state = TaskTreeViewController.SelectionState.MULTIPLE_HETERGENOUS
        else:
            self._tasklist_selection_state = TaskTreeViewController.SelectionState.NONE
        
        if len(self._selected_tasks) == 1:
            self._task_selection_state = TaskTreeViewController.SelectionState.SINGLE
        elif len(self._selected_tasks) > 1:
            # Determine if all selected tasks belong to the same tasklist or
            # not.
            is_homogenous = True
            prev_tasklist_id = None
            for selected_task in self._selected_tasks:
                if prev_tasklist_id is not None and selected_task.tasklist_id != prev_tasklist_id:
                    is_homogenous = False
                    break
            
            if is_homogenous:
                self._task_selection_state = TaskTreeViewController.SelectionState.MULTIPLE_HOMOGENOUS
            else:
                self._task_selection_state = TaskTreeViewController.SelectionState.MULTIPLE_HETERGENOUS
        else:
            self._task_selection_state = TaskTreeViewController.SelectionState.NONE
                                    
        # Notify any listeners of the change in selection state.
        # TODO: Make this a bit smarter/more efficient by only firing when the
        # selection state actually changes, instead of on every selection 
        # event.
        self.selection_state_changed.fire(self._tasklist_selection_state, self._task_selection_state)  
        
    class TreeState(object):
        """
        Very simple convenience class to group the two tree node states 
        together.
        """
        def __init__(self, is_expanded=False, is_selected=False):
            self.is_expanded = is_expanded
            self.is_selected = is_selected      
        
    class SelectionState(object):
            NONE = 0
            SINGLE = 1
            MULTIPLE_HOMOGENOUS = 2 # All in same tasklist
            MULTIPLE_HETERGENOUS = 3 # In different tasklists
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
        self.icon_title_column.add_attribute(self.image_renderer, "pixbuf", TreeNode.ICON)
        self.icon_title_column.add_attribute(self.title_renderer, "text", TreeNode.LABEL)        
        self.append_column(self.icon_title_column)
        
        # Set the selection mode to allow multiple nodes to be selected
        # simultaneously.
        self.get_selection().set_mode(Gtk.SelectionMode.MULTIPLE)
        
        # Set the scrolling property???
        self.set_vscroll_policy(Gtk.ScrollablePolicy.NATURAL)
        self.set_hscroll_policy(Gtk.ScrollablePolicy.NATURAL)
        
    def start_editing(self, treepath):
        self.get_selection().select_path(treepath.to_string())
        self.scroll_to_cell(treepath.to_string())
        self.set_cursor_on_cell(treepath, self.icon_title_column, self.title_renderer, start_editing=True)
#------------------------------------------------------------------------------ 

class BinaryIconButton(Gtk.Button):
    def __init__(self, icon_file_path, disabled_icon_file_path=None, is_enabled=True):
        Gtk.Button.__init__(self)
        
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
