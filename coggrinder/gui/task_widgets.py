"""
Created on Mar 29, 2012

@author: Clay Carpenter
"""
from gi.repository import Gtk
from coggrinder.entities.tasks import TaskList, Task
from coggrinder.resources.icons import buttons
from coggrinder.gui.events import Event
from coggrinder.gui.task_treestore import TaskTreeStore, TaskTreeStoreNode
from coggrinder.entities.tasktree import TaskTree, TaskTreeComparator
import copy
import pprint
from datetime import datetime
from coggrinder.services.task_services import UnregisteredEntityError

class TaskTreeWindowController(object):
    def __init__(self, tasktree_service=None):
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
        self.view.edit_task_button_clicked.register(self._handle_edit_task_details_event)
        self.view.complete_task_button_clicked.register(self._handle_complete_task_event)
        self.view.remove_task_button_clicked.register(self._handle_remove_task_event)

        self.view.promote_task_button_clicked.register(self._handle_promote_task_event)
        self.view.demote_task_button_clicked.register(self._handle_demote_task_event)
        self.view.reorder_task_up_button_clicked.register(self._handle_reorder_task_up_event)
        self.view.reorder_task_down_button_clicked.register(self._handle_reorder_task_down_event)

        self.view.configure_button_clicked.register(self._handle_configure_event)

        self.view.entity_title_edited.register(self._handle_entity_title_updated)

    def refresh_task_data(self):
        """Pull updated tasklist and task information from the task tree
        services Store the updated results locally.
        """
        # Pull updated task data (tasklists and tasks) from the services.
        self._tasktree_service.refresh_task_data()
        
        self.build_task_view()        

    def refresh_task_view(self):
        """ Refreshing the UI task tree.

        This allows the UI to display any changes to the underlying task data.
        """
        # Update the UI task tree.
        self.view.update_tasktree(self._tasktree_service.tree)
        
    def refresh_view(self):
        """Refreshes the entire UI, including the task tree and the toolbar
        states.
        """
        # Refresh the task tree UI.
        self.refresh_task_view()
        
        # Update the toolbar button states.
        self.view.update_button_states()
        
    def build_task_view(self):
        # Build the task tree view from a the TaskTreeService's TaskTree 
        # task data set.
        self.view.build_tasktree(self._tasktree_service.tree)

    def _handle_save_event(self, button):
        self._tasktree_service.push_task_data()

    def _handle_sync_event(self, button):
        self._tasktree_service.pull_task_data()

    def _handle_revert_event(self, button):        
        # Clear away any user changes.
        self._tasktree_service.revert_task_data()
        
        # Update the task tree UI with the scrubbed task data.
        self.build_task_view()

        # Refresh the UI.
        self.refresh_view()
        
        # Clear away any existing tree selections.
        self.clear_treeview_state()

    def _handle_add_list_event(self, button):
        # Create the new (blank) TaskList, and add it to the task data.
        new_tasklist = self._tasktree_service.add_entity(TaskList(title=""))
        
        # Update the UI with the new TaskList.
        self.refresh_view()

        # Find the new TaskList, select it (wiping out other selections), and
        # set it to editable/editing.
        self.view.set_entity_editable(new_tasklist)

    def _handle_remove_list_event(self, button):
        # Locate the selected TaskList.
        selected_entities = self.view.get_selected_tasklists()
        assert len(selected_entities) == 1, "Should only allow a single TaskList to be selected for deletion."
        tasklist = selected_entities[0]

        # Delete the TaskList.
        self._tasktree_service.delete_entity(tasklist)

        # Refresh the UI.
        self.refresh_view()

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
        new_task = Task(title="", parent_id=parent_id, tasklist_id=tasklist_id)

        # Add the new task.
        new_task = self._tasktree_service.add_entity(new_task)

        # Refresh the task tree UI.
        self.refresh_task_view()

        # Override existing selection. Select new task and set the tree node 
        # to be "editable". This will need to expand any collapsed parent nodes
        # in order to get the selection properly set. Otherwise, by default the 
        # new node could be hidden.
        self.view.set_entity_editable(new_task)

    def _handle_edit_task_details_event(self, button):
        raise NotImplementedError

    def _handle_complete_task_event(self, button):
        raise NotImplementedError

    def _handle_remove_task_event(self, button):
        # Locate the selected task or tasks.
        selected_tasks = self.view.get_selected_tasks()
        assert len(selected_tasks) > 0
        
        # For each task, delete the task. The service layer will handle 
        # promoting any children of the task to 
        # be children of the task's parent (task or tasklist).
        # Keep track of the child tasks that have their parent updated, as 
        # they will need to be updated as well.
        for selected_task in selected_tasks:
            self._tasktree_service.delete_entity(selected_task)

        # Update the UI.
        self.refresh_view()

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

    def _handle_entity_title_updated(self, target_entity_id, updated_title):
        # Get the entity from the TaskTreeService.
        target_entity = self._tasktree_service.get_entity_for_id(target_entity_id)
        
        # Set the entity's updated title.
        target_entity.title = updated_title
      
        # Send the updated entity to the TaskTreeService.
        target_entity = self._tasktree_service.update_entity(target_entity)
        
        # Reorder the tree.
        self._tasktree_service.tree.sort() 

        # Update the task data view.
        self.refresh_view()

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
        self.refresh_view()
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
        
    def build_tasktree(self, tasktree):
        self.treeview_controller.build_tasktree(tasktree)
            
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
        return self.treeview_controller.selected_entities
    
    def get_selected_tasklists(self):
        return self.treeview_controller.selected_tasklists
    
    def get_selected_tasks(self):
        return self.treeview_controller.selected_tasks
    
    def clear_treeview_state(self):
        self.treeview_controller.clear_treeview_state()
    
    def refresh_treeview_state(self):
        self.treeview_controller.refresh_treeview_state()
    
    def clear_treeview_selections(self):
        self.treeview_controller.clear_treeview_selections()
        
    def update_button_states(self):
        selection_state = self.treeview_controller.selection_state
        self.toolbar_controller.selection_state_changed(selection_state)
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

    def selection_state_changed(self, tasktree_selection_state):
        self.view.update_button_states(tasktree_selection_state)
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
        self.save_button = BinaryIconButton(buttons.FILES["save.png"], is_enabled=True)
        button_box.add(self.save_button)

        self.sync_button = BinaryIconButton(buttons.FILES["sync.png"])
        button_box.add(self.sync_button)

        self.revert_button = BinaryIconButton(buttons.FILES["revert.png"], is_enabled=True)
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
    def update_button_states(self, tasktree_selection_state):        
        # Only enable when single TaskList is selected.
        self.remove_list_button.set_state(
            tasktree_selection_state.tasklist_selection_state == TaskTreeSelectionState.SINGLE)

        # Only show add task when a single row/entity--either task or 
        # TaskList--is selected:
        # -- Task single and TaskList none or
        # -- Task none and TaskList single
        add_task_button_enabled = False
        if ((tasktree_selection_state.task_selection_state == TaskTreeSelectionState.SINGLE and tasktree_selection_state.tasklist_selection_state == TaskTreeSelectionState.NONE) 
            or (tasktree_selection_state.task_selection_state == TaskTreeSelectionState.NONE and tasktree_selection_state.tasklist_selection_state == TaskTreeSelectionState.SINGLE)):
            add_task_button_enabled = True
            
        self.add_task_button.set_state(add_task_button_enabled)

        # Show whenever task or tasks are selected, regardless of tasklist.
        task_detail_buttons_enabled = False
        if tasktree_selection_state.task_selection_state != TaskTreeSelectionState.NONE:
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
    def __init__(self, tasktree=None):
        self.view = TaskTreeView()
        
        if tasktree is None:
            tasktree = TaskTree()
        self._tasktree = tasktree

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

        # TODO: Document the expected keys and values for this TreeState dict; 
        # how it will be used.
        self._clear_tree_state()

        # Set default for clearing flag. This flag is used to help ignore 
        # "system" selection change events that seem to occur during the 
        # Gtk.TreeStore.clear() operation.
        self._is_clearing = False

        # Connect the tree store/row_data to the tree view.
        self.view.set_model(self.task_treestore)
        
    @property
    def selection_state(self):
        return TaskTreeSelectionState(selected_tasks=self.selected_tasks,
            selected_tasklists=self.selected_tasklists)

    @property
    def selected_entities(self):
        return [state for state in self.tree_states if state.is_selected]
    
    @property
    def selected_tasklists(self):
        return [state for state in self.selected_entities
                if self.has_tasklist_path(state.entity_id)]
    
    @property
    def selected_tasks(self):
        return [state for state in self.selected_entities
                if not self.has_tasklist_path(state.entity_id)]
        
    @property
    def tree_states(self):
        return self._tree_states.values()
        
    def build_tasktree(self, tasktree):
        # Build a new TaskTreeStore (Gtk TreeStore) with the updated task data.
        self._tasktree = copy.deepcopy(tasktree)
        self.task_treestore.build_tree(tasktree)       
        
        self.refresh_treeview_state() 

    def update_tasktree(self, updated_tasktree):
        """Collect the current tree state, replace the tree model, and then
        restore the tree state (as much as possible).
        """
        
        # Pass the updates along to the task tree store.
        self.refresh_treeview_state()
        self.task_treestore.build_tree(updated_tasktree)
        self._tasktree = copy.deepcopy(updated_tasktree)
        self._restore_tree_state()
        
        self.refresh_treeview_state()

    def set_entity_editable(self, entity):
        # Find the entity within the task tree.        
        entity_tree_path = self.task_treestore.get_path_for_entity_id(entity.entity_id)
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
    
    def has_tasklist_path(self, entity_id):
        # Find the treestore path registered to the entity ID, and split it
        # into its individual branch indices.
        treestore_path = self.task_treestore.get_path_for_entity_id(entity_id)        
        treestore_indices = treestore_path.split(":")
        
        return len(treestore_indices) == 1

    def refresh_treeview_state(self):        
        # Clear out existing tree states.
        self._clear_tree_state()

        # Collect the existing current state of the tree view.
        self._collect_tree_state()
        
        # TODO: Remove print debug statements.
        print "\nRefreshed treeview states:"
        pprint.pprint(self.tree_states, indent=4, width=1)
        print    
        
    def clear_treeview_state(self):
        # Clear existing tree state information.
        self._clear_tree_state()
        
        # Collapse any tree expansions.
        self.view.collapse_all()
        
        # Clear any existing selections. This must be called after the tree
        # is fully collapsed or selections can survive the refresh.
        self.clear_treeview_selections()
        
    def clear_treeview_selections(self):
        self.view.get_selection().unselect_all()
    
    def _clear_tree_state(self):
        self._tree_states = dict()

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
                entity_id = self.task_treestore[tree_iter][TaskTreeStoreNode.ENTITY_ID]
                
                self._tree_states[entity_id] = self.TreeState(entity_id, is_expanded, is_selected)

            if self.task_treestore.iter_has_child(tree_iter):
                child_iter = self.task_treestore.iter_children(tree_iter)

                self._collect_tree_state(child_iter)

            tree_iter = self.task_treestore.iter_next(tree_iter)

    def _restore_tree_state(self):
        # TODO: Remove debug print statements.
        print "Restoring tree states..."
        
        # Filter out tree states that are no longer valid.
        self._prune_tree_states()
        
        for tree_row_state in self.tree_states:
            print "\t restoring:{0}".format(tree_row_state)
            
            treestore_path_str = self.task_treestore.get_path_for_entity_id(tree_row_state.entity_id)
            treestore_iter = self.task_treestore.get_iter(treestore_path_str)
            treestore_path = self.task_treestore.get_path(treestore_iter)
            
            print "\t Current treestore path: {0}".format(treestore_path_str)
            
            if tree_row_state.is_expanded:
                self.view.expand_row(treestore_path, False)

            if tree_row_state.is_selected:
                self.view.get_selection().select_path(treestore_path)
                
    def _prune_tree_states(self):
        self._tree_states = {state.entity_id: state for state 
                            in self.tree_states 
                            if self._tree_state_is_valid(state)}

    def _tree_state_is_valid(self, tree_row_state):
        try:
            treestore_path = self.task_treestore.get_path_for_entity_id(tree_row_state.entity_id)
        except UnregisteredEntityError:
            print "Invalid tree state: {0}".format(tree_row_state)
            return False
        
        return tree_row_state.is_expanded or tree_row_state.is_selected
                
    def _handle_cell_edited(self, tree_title_cell, tree_path, updated_title):
        # Find the entity that was edited through the tree view.
        target_entity_id = self.task_treestore.get_entity_id_for_path(tree_path)

        # Fire event, sending along the target entity ID and the
        # updated title text.
        self.entity_title_edited.fire(target_entity_id, updated_title)

    def _handle_selection_changed(self, selection_data):
        has_selected_rows = True
        if selection_data.count_selected_rows() == 0:
            has_selected_rows = False
        
        # If the updating flag is set, or if no rows have been selected, 
        # return immediately to prevent handling spurious selection 
        # change events (fired by Gtk in response to tree model changes?).        
        if self.task_treestore.is_updating_tree or not has_selected_rows:       
            return
        
        # Clear out current selection states.
        for tree_state in self.tree_states:
            tree_state.is_selected = False
            
        # Filter out tree states that are no longer valid.
        self._prune_tree_states()
            
        self._collect_tree_state()
                       
        # TODO: Remove this debug print statement.
        print "\nTreeview states after sel change:"
        pprint.pprint(self.tree_states, indent=4, width=1)
        print    
                        
        """
        TODO: Make this a bit smarter/more efficient by only firing when the
        selection state actually changes, instead of on every selection 
        event.
        """
        # Notify any listeners of the change in selection state.
        self.selection_state_changed.fire(self.selection_state)

    class TreeState(object):
        """
        Very simple convenience class to group the two tree node states
        (is expanded, is selected) together.
        """
        def __init__(self, entity_id, is_expanded=False, is_selected=False):
            self.entity_id = entity_id
            self.is_expanded = is_expanded
            self.is_selected = is_selected
    
        def __str__(self):
            info_str = "<id: {id} expnd: {expanded}; slctd: {selected};>"
            info_str = info_str.format(expanded=self.is_expanded,
                selected=self.is_selected,
                id=self.entity_id)
            
            return info_str
        
        def __repr__(self):
            return self.__str__()
#------------------------------------------------------------------------------ 

class TaskTreeSelectionState(object):
    NONE = 0
    SINGLE = 1
    # All selections are in the same tasklist.
    MULTIPLE_HOMOGENOUS = 2 
    # Selections are spread across multiple tasklists.
    MULTIPLE_HETEROGENOUS = 3 
            
    def __init__(self, selected_tasks=None, selected_tasklists=None):
        if selected_tasks is None:
            selected_tasks = list()
        if selected_tasklists is None:
            selected_tasklists = list()
            
        self.selected_tasks = selected_tasks
        self.selected_tasklists = selected_tasklists
        
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

            if is_homogenous:
                return TaskTreeSelectionState.MULTIPLE_HOMOGENOUS
            else:
                return TaskTreeSelectionState.MULTIPLE_HETEROGENOUS
        
        return TaskTreeSelectionState.NONE
        
    @property
    def selected_entities(self):
        return self.selected_tasks + self.selected_tasklists
    
    def __str__(self):
        info_str = "<TL state: {tl_state}; T state: {t_state}; Slctd: {slctd};>"
        info_str = info_str.format(tl_state=self.tasklist_selection_state,
            t_state=self.task_selection_state, slctd=self.selected_entities)
        
        return info_str
    
    def __repr__(self):
        return self.__str__()
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
