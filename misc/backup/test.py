"""
Created on Mar 28, 2012

@author: Clay Carpenter
"""
from gi.repository import Gtk, GdkPixbuf

class TaskTreeWindow(Gtk.Window):
    def __init__(self):
        Gtk.Window.__init__(self, title="CogGrinder")
                               
        self.set_default_size(400, 400)
        self.model = Gtk.TreeStore(str, GdkPixbuf.Pixbuf)
        
        image = Gtk.Image.new_from_file(
            "/home/clay/Dropbox/work/projects/python/coggrinder/misc/icons/notepad.png")
        notebook_icon = image.get_pixbuf()
        
        image = Gtk.Image.new_from_file(
            "/home/clay/Dropbox/work/projects/python/coggrinder/misc/icons/checkbox_unchecked.png")
        unchecked_icon = image.get_pixbuf()
        
        self.treeview = Gtk.TreeView(model=self.model)
        self.tree_selection = self.treeview.get_selection()
        self.tree_selection.set_mode(Gtk.SelectionMode.MULTIPLE)
        self.tree_selection.connect("changed", self.task_selection_changed)
        
        self.text_renderer = Gtk.CellRendererText()     
        self.text_renderer.set_property("wrap-width", 200)
        print self.text_renderer.get_property("editable")
        print self.text_renderer.set_property("editable", True)
        print self.text_renderer.get_property("editable")
        
        self.text_renderer.connect("edited", self.test_cell_edited)
        
        self.image_renderer = Gtk.CellRendererPixbuf()
#        self.image_renderer.set_fixed_size(30, 30)
                
#        self.column = Gtk.TreeViewColumn("Task Name", self.text_renderer, text=0)
        self.column = Gtk.TreeViewColumn("Task Name")
        self.column.pack_start(self.image_renderer, False)
        self.column.pack_end(self.text_renderer, True)
        self.column.add_attribute(self.image_renderer, "pixbuf", 1)
        self.column.add_attribute(self.text_renderer, "text", 0)
        
        
#        self.icon_column = Gtk.TreeViewColumn("", self.image_renderer, pixbuf=1)
        
#        self.treeview.append_column(self.icon_column)
        self.treeview.append_column(self.column)
        
        self.layout_box = Gtk.Box(spacing=0)
        self.layout_box.set_orientation(Gtk.Orientation.VERTICAL)
        self.layout_box.pack_end(self.treeview, True, True, 0)
        
        self.toolbar_box = Gtk.HBox(spacing=10)
        
        test_image = Gtk.Image.new_from_file(
            "/home/clay/Dropbox/work/projects/python/coggrinder/misc/icons/notepad.png")
        self.clicky_image_button = Gtk.Button()
        self.clicky_image_button.add(test_image)
        self.clicky_image_button.connect("clicked", self.clicky_clicked)
        self.toolbar_box.pack_start(self.clicky_image_button, False, False, 0)
        
        self.layout_box.pack_end(self.toolbar_box, False, False, 0)
        
        root_iter = self.model.get_iter_first()
        
        self.model.append(root_iter, ["TaskList 1", notebook_icon])
        task_2_iter = self.model.append(root_iter, ["TaskList 2", notebook_icon])
        self.model.append(task_2_iter, ["Task 2.1", unchecked_icon])
        self.model.append(task_2_iter, ["Task 2.2", unchecked_icon])
        self.model.append(task_2_iter, ["Task 2.3", unchecked_icon])
        task_2d_iter = self.model.append(task_2_iter, ["Task 2d", notebook_icon])
        self.model.append(task_2d_iter, ["Task 2d1", unchecked_icon])
        self.model.append(task_2d_iter, ["Task 2d2", unchecked_icon])
        self.model.append(task_2d_iter, ["Task 2d3", unchecked_icon])
        self.model.append(root_iter, ["TaskList 3", notebook_icon])
        
        self.add(self.layout_box)
        
    def task_selection_changed(self, selection):        
        print "Selection change event detected..."
        
    def clicky_clicked(self, button):
        print "Clicky clicked 2..."
        treestore, selected_rows = self.tree_selection.get_selected_rows()
        for row in selected_rows:
            print "Selected: {0}".format(self.model[row][0])
        
    def test_cell_edited(self, widget, path, new_text):
        edit_iter = win.model.get_iter(path)
        win.model[edit_iter][0] = new_text
#------------------------------------------------------------------------------

 
win = None

if __name__ == '__main__':
#    win = CellRendererToggleWindow()
    win = TaskTreeWindow()
    win.connect("delete-event", Gtk.main_quit)
    win.show_all()
    Gtk.main()
