import numpy as np
import os
import tkinter as tk
from tkinter import ttk, filedialog, messagebox, Tk
from PIL import Image, ImageTk
from matplotlib.colors import rgb2hex, to_rgb
from matplotlib.colors import LinearSegmentedColormap


class AutoScrollbar(ttk.Scrollbar):
    """A scrollbar that hides itself if it's not needed
    Works only if you use the grid geometry manager"""

    def set(self, lo, hi):
        if float(lo) <= 0.0 and float(hi) >= 1.0:
            self.grid_remove()
        else:
            self.grid()
            ttk.Scrollbar.set(self, lo, hi)

    def pack(self, **kw):
        raise tk.TclError('Cannot use pack with this widget')

    def place(self, **kw):
        raise tk.TclError('Cannot use place with this widget')


class ZoomAdvanced(ttk.Frame):
    """Advanced zoom of the image"""

    def __init__(self, mainframe, path):
        """Initialize the main frame"""
        ttk.Frame.__init__(self, master=mainframe)
        self.filename = path.split('/')[-1]
        self.master.title(self.filename)
        # The main frame onto which we draw the app's elements
        frame = tk.Frame(self.master)
        frame.grid(row=0)
        # Add a button to clear the grid
        b_clear = tk.Button(frame, text='Clear', command=self.clear_grid)
        b_clear.grid(row=0, column=1, padx=5, pady=5)
        # Add a button to save
        b_save = tk.Button(frame, text='Export Tiles', command=self.save_curation)
        b_save.grid(row=0, column=2, padx=5, pady=5)
        # The palette for selecting colours.
        self.num_colors = 10
        self.palette_canvas = tk.Canvas(self.master, height=75, width=60 * (self.num_colors + 1))
        self.palette_canvas.grid(row=1, column=0)
        colors = [(1, 0.5, 0.5), (0.6, 0.25, 0.7), (0.05, 0.05, 1)]
        color_map = LinearSegmentedColormap.from_list('Yeet', colors, N=10)
        self.colors = ['']
        for i in range(self.num_colors):
            color = rgb2hex(color_map(i)[:3])
            self.colors.append(color)
        # Add the color selection rectangles to the palette canvas
        self.palette_rects = []
        self.p_pad = 5
        self.labels = [""] + [i for i in range(10)]
        self.p_width = self.p_height = 65 - 2 * self.p_pad
        for i in range(self.num_colors + 1):
            x, y = self.p_pad * (i + 1) + i * self.p_width, self.p_pad
            rect = self.palette_canvas.create_rectangle(x, y,
                                                        x + self.p_width, y + self.p_height, fill=self.colors[i])
            self.palette_rects.append(rect)
            self.palette_canvas.create_text((2 * x + self.p_width) / 2, (2 * y + self.p_height) / 2,
                                            font=("Purisa", 16), fill="black", text="{}".format(self.labels[i]))
        self.palette_canvas.create_polygon([self.p_pad, self.p_pad, self.p_width + self.p_pad,
                                            self.p_height + self.p_pad], outline="black", fill="black", width=1)
        self.palette_canvas.create_polygon([self.p_pad, self.p_height + self.p_pad, self.p_width + self.p_pad,
                                            self.p_pad], outline="black", fill="black", width=1)
        self.current_color = 0
        # Vertical and horizontal scrollbars for canvas
        vbar = AutoScrollbar(self.master, orient='vertical')
        hbar = AutoScrollbar(self.master, orient='horizontal')
        vbar.grid(row=2, column=1, sticky='ns')
        hbar.grid(row=4, column=0, sticky='we')
        self.orig_image = np.array(Image.open(path))  # open image
        self.image = Image.open(path)  # open image
        self.width, self.height = self.image.size
        self.im_scale = 1.0  # scale for the canvas image
        self.delta = 1.1  # zoom magnitude
        # Scale image to the window when it first pops up
        if self.width > 1024 or self.height > (768 - 200):
            ratio_scale = max(self.width / 1024, self.height / (768 - 200))
            resized_width = self.width / ratio_scale
            resized_height = self.height / ratio_scale
        # Create canvas and put image on it
        self.canvas = tk.Canvas(self.master, highlightthickness=0, width=resized_width, height=resized_height,
                                xscrollcommand=hbar.set, yscrollcommand=vbar.set)
        self.canvas.grid(row=2, column=0, sticky='nswe')
        self.canvas.update()  # wait till canvas is created
        vbar.configure(command=self.scroll_y)  # bind scrollbars to the canvas
        hbar.configure(command=self.scroll_x)
        # Make the canvas expandable
        self.master.rowconfigure(2, weight=1)
        self.master.columnconfigure(0, weight=1)
        # Put image into container rectangle and use it to set proper coordinates to the image
        self.container = self.canvas.create_rectangle(0, 0, self.width, self.height, width=0, tags="image")
        # Add the cell rectangles to the grid canvas.
        self.orig_x_tile, self.x_tile = 128, 128
        self.orig_y_tile, self.y_tile = 128, 128
        self.cells = []
        self.num_x_tiles = int(self.width / self.x_tile)
        self.num_y_tiles = int(self.height / self.y_tile)
        for iy in range(self.num_y_tiles):
            for ix in range(self.num_x_tiles):
                x, y = ix * self.x_tile, iy * self.y_tile
                rect = self.canvas.create_rectangle(x, y, x + self.x_tile, y + self.y_tile, fill="",
                                                    tags=str(x) + ' ' + str(y))
                self.cells.append(rect)
        self.tile_colors = np.zeros((self.num_x_tiles, self.num_y_tiles))
        # Bind events to the Canvas
        self.hovering_tile = None
        imagetk = ImageTk.PhotoImage(self.image)
        self.canvas.create_image(0, 0, anchor='nw', image=imagetk)
        # Scale image to the window when it first pops up
        if self.width > 1024 or self.height > (768 - 200):
            ratio_scale = max(self.width / 1024, self.height / (768 - 200))
            scale = 1.0
            self.im_scale /= ratio_scale
            self.x_tile /= ratio_scale
            self.y_tile /= ratio_scale
            scale /= ratio_scale
            self.canvas.scale('all', 0, 0, scale, scale)  # rescale all canvas objects
            self.canvas.config(width=self.width / ratio_scale, height=self.height / ratio_scale)
        self.canvas.bind('<Configure>', self.show_image)  # canvas is resized
        self.canvas.bind('<ButtonPress-1>', self.move_from)
        self.canvas.bind('<B1-Motion>', self.move_to)
        self.canvas.bind('<MouseWheel>', self.wheel)  # with Windows and MacOS, but not Linux
        self.canvas.bind('<Button-5>', self.wheel)  # only with Linux, wheel scroll down
        self.canvas.bind('<Button-4>', self.wheel)  # only with Linux, wheel scroll up
        self.palette_canvas.bind('<ButtonPress-1>', self.palette_click_callback)  # palette canvas
        self.canvas.bind('<Double-Button-1>', self.w_click_callback)  # grid canvas
        self.canvas.bind('<Motion>', self.hover_tile)
        self.canvas.bind('<Enter>', self.hover_tile)
        self.canvas.bind('<Leave>', self.left_grid)
        self.reference_image = self.image
        self.show_image()

    def palette_click_callback(self, event):
        """Function called when someone clicks on the palette canvas"""
        x, y = event.x, event.y
        # Did the user click a color from the palette?
        if self.p_pad < y < self.p_height + self.p_pad:
            # Index of the selected palette rectangle
            ic = x // (self.p_width + self.p_pad)
            # X-position with respect to the palette rectangle left edge
            xp = x - ic * (self.p_width + self.p_pad) - self.p_pad
            # Is the index valid and the click within the rectangle?
            if ic < self.num_colors + 1 and 0 < xp < self.p_width:
                self.select_color(ic)

    def w_click_callback(self, event):
        """Function called when someone clicks on the grid canvas"""
        bbox1 = self.canvas.bbox(self.container)  # get image area
        bbox2 = (self.canvas.canvasx(0),  # get visible area of the canvas
                 self.canvas.canvasy(0),
                 self.canvas.canvasx(self.canvas.winfo_width()),
                 self.canvas.canvasy(self.canvas.winfo_height()))
        # Get coordinates of the current zoomed/panned area
        top_left = abs(bbox1[0] - bbox2[0]), abs(bbox2[1] - bbox1[1])
        bottom_right = min(bbox1[2], bbox2[2]), min(bbox1[3], bbox2[3])
        # Do nothing if the user clicked on a cell outside the grid
        if bbox1[0] > bbox2[0]:
            if not top_left[0] < event.x < bottom_right[0]:
                return
        if bbox1[1] > bbox2[1]:
            if not top_left[1] < event.y < bottom_right[1]:
                return
        # Index into the grid of cells
        x, y = event.x + top_left[0], event.y + top_left[1]
        if bbox1[0] > bbox2[0]:
            x = event.x - top_left[0]
        if bbox1[1] > bbox2[1]:
            y = event.y - top_left[1]
        ix = int(x // self.x_tile)
        iy = int(y // self.y_tile)
        if ix < self.num_x_tiles and iy < self.num_y_tiles:
            i = iy * self.num_x_tiles + ix
            self.tile_colors[ix, iy] = self.current_color
            self.color_tile(self.cells[i], self.colors[self.current_color])

    def hover_tile(self, event):
        """Function called when someone hovers over the grid canvas"""
        if np.sum(self.tile_colors) == 0:
            return
        bbox1 = self.canvas.bbox(self.container)  # get image area
        bbox2 = (self.canvas.canvasx(0),  # get visible area of the canvas
                 self.canvas.canvasy(0),
                 self.canvas.canvasx(self.canvas.winfo_width()),
                 self.canvas.canvasy(self.canvas.winfo_height()))
        # Get coordinates of the current zoomed/panned area
        top_left = abs(bbox1[0] - bbox2[0]), abs(bbox2[1] - bbox1[1])
        # Index into the grid of cells
        x, y = event.x + top_left[0], event.y + top_left[1]
        if bbox1[0] > bbox2[0]:
            x = event.x - top_left[0]
        if bbox1[1] > bbox2[1]:
            y = event.y - top_left[1]
        ix = int(x // self.x_tile)
        iy = int(y // self.y_tile)
        if ix < self.num_x_tiles and iy < self.num_y_tiles:
            i = iy * self.num_x_tiles + ix
            tags = self.canvas.gettags(self.cells[i])
            x, y = int(tags[0]), int(tags[1])
            x_h, y_h = self.hovering_tile[0], self.hovering_tile[1]
            if x_h == x and y_h == y:  # do nothing if mouse is over the same tile
                return
            self.image = Image.fromarray(self.reference_image)
            self.hovering_tile = [x, y]
            original_tile = self.orig_image[y:y + 128, x:x + 128]
            img_array = np.array(self.image)
            img_array[y:y + 128, x:x + 128, :] = original_tile
            self.image = Image.fromarray(img_array)
            self.show_image()
        else:
            self.image = Image.fromarray(self.reference_image)
            self.show_image()

    def left_grid(self, event):
        if np.sum(self.tile_colors) == 0:
            return
        self.image = Image.fromarray(self.reference_image)
        self.show_image()
        self.hovering_tile[0], self.hovering_tile[1] = -1, -1

    def color_tile(self, item, color):
        tags = self.canvas.gettags(item)
        x, y = int(tags[0]), int(tags[1])
        tile = self.orig_image[y:y + 128, x:x + 128]
        if color != "":
            tile = (to_rgb(color) * tile).astype(np.uint8)
        img_array = np.array(self.image)
        img_array[y:y + 128, x:x + 128, :] = tile
        self.image = Image.fromarray(img_array)
        self.hovering_tile = [x, y]
        self.reference_image = img_array
        self.show_image()

    def scroll_y(self, *args, **kwargs):
        """Scroll canvas vertically and redraw the image"""
        self.canvas.yview(*args, **kwargs)  # scroll vertically
        self.show_image()  # redraw the image

    def scroll_x(self, *args, **kwargs):
        """Scroll canvas horizontally and redraw the image"""
        self.canvas.xview(*args, **kwargs)  # scroll horizontally
        self.show_image()  # redraw the image

    def move_from(self, event):
        """Remember previous coordinates for scrolling with the mouse"""
        self.canvas.scan_mark(event.x, event.y)

    def move_to(self, event):
        """Drag (move) canvas to the new position"""
        self.canvas.scan_dragto(event.x, event.y, gain=1)
        self.show_image()  # redraw the image

    def initialize(self):
        """Scale image to the window when it first pops up"""
        if self.width > 1024 or self.height > (768 - 200):
            ratio_scale = max(self.width / 1024, self.height / (768 - 200))
            scale = 1.0
            self.im_scale /= ratio_scale
            self.x_tile /= ratio_scale
            self.y_tile /= ratio_scale
            scale /= ratio_scale
            self.canvas.scale('all', 0, 0, scale, scale)  # rescale all canvas objects
            self.canvas.config(width=self.width / ratio_scale, height=self.height / ratio_scale)
        else:
            self.show_image()

    def wheel(self, event):
        """Zoom with mouse wheel"""
        x = self.canvas.canvasx(event.x)
        y = self.canvas.canvasy(event.y)
        bbox = self.canvas.bbox(self.container)  # get image area
        if bbox[0] < x < bbox[2] and bbox[1] < y < bbox[3]:
            pass  # Ok! Inside the image
        else:
            return  # zoom only inside image area
        scale = 1.0
        # Respond to Linux (event.num) or Windows (event.delta) wheel event
        if event.num == 5 or event.delta < 0:  # scroll down
            i = min(self.width, self.height)
            if int(i * self.im_scale) < 30:
                return  # image is less than 30 pixels
            self.im_scale /= self.delta
            self.x_tile /= self.delta
            self.y_tile /= self.delta
            scale /= self.delta
        if event.num == 4 or event.delta > 0:  # scroll up
            i = min(self.canvas.winfo_width(), self.canvas.winfo_height())
            if i < self.im_scale:
                return  # 1 pixel is bigger than the visible area
            self.im_scale *= self.delta
            self.x_tile *= self.delta
            self.y_tile *= self.delta
            scale *= self.delta
        self.canvas.scale('all', x, y, scale, scale)  # rescale all canvas objects
        self.show_image()

    def show_image(self, event=None):
        """Show image on the Canvas"""
        bbox1 = self.canvas.bbox(self.container)  # get image area
        bbox2 = (self.canvas.canvasx(0),  # get visible area of the canvas
                 self.canvas.canvasy(0),
                 self.canvas.canvasx(self.canvas.winfo_width()),
                 self.canvas.canvasy(self.canvas.winfo_height()))
        bbox = [min(bbox1[0], bbox2[0]), min(bbox1[1], bbox2[1]),  # get scroll region box
                max(bbox1[2], bbox2[2]), max(bbox1[3], bbox2[3])]
        if bbox[0] == bbox2[0] and bbox[2] == bbox2[2]:  # whole image in the visible area
            bbox[0] = bbox1[0]
            bbox[2] = bbox1[2]
        if bbox[1] == bbox2[1] and bbox[3] == bbox2[3]:  # whole image in the visible area
            bbox[1] = bbox1[1]
            bbox[3] = bbox1[3]
        self.canvas.configure(scrollregion=bbox)  # set scroll region
        x1 = max(bbox2[0] - bbox1[0], 0)  # get coordinates (x1,y1,x2,y2) of the image tile
        y1 = max(bbox2[1] - bbox1[1], 0)
        x2 = min(bbox2[2], bbox1[2]) - bbox1[0]
        y2 = min(bbox2[3], bbox1[3]) - bbox1[1]
        if int(x2 - x1) > 0 and int(y2 - y1) > 0:  # show image if it in the visible area
            x = min(int(x2 / self.im_scale), self.width)  # sometimes it is larger on 1 pixel...
            y = min(int(y2 / self.im_scale), self.height)  # ...and sometimes not
            image = self.image.crop((int(x1 / self.im_scale), int(y1 / self.im_scale), x, y))
            imagetk = ImageTk.PhotoImage(image.resize((int(x2 - x1), int(y2 - y1))))
            imageid = self.canvas.create_image(max(bbox2[0], bbox1[0]), max(bbox2[1], bbox1[1]),
                                               anchor='nw', image=imagetk)
            self.canvas.lower(imageid)  # set image into background
            self.canvas.imagetk = imagetk  # keep an extra reference to prevent garbage-collection

    def select_color(self, i):
        """Select the color indexed at i in the colors list."""
        self.palette_canvas.itemconfig(self.palette_rects[self.current_color],
                                       outline='black', width=1)
        self.current_color = i
        self.palette_canvas.itemconfig(self.palette_rects[self.current_color],
                                       outline='black', width=5)

    def save_curation(self):
        """Output folders with curated images"""
        if np.sum(self.tile_colors) == 0:
            messagebox.showwarning("", "No colored tiles to save.")
            return
        if np.count_nonzero(self.tile_colors) < (self.num_x_tiles * self.num_y_tiles):
            to_proceed = messagebox.askokcancel("", "Not all tiles were colored. Do you want to proceed?")
            if not to_proceed:
                return
        if not os.path.exists("Curated_Images"):
            os.mkdir("Curated_Images")
        window = tk.Toplevel()
        window.geometry("320x65+450+175")
        frame = tk.Frame(window, width=350, height=80)
        frame.grid()
        tk.Label(frame, text="Progress...").grid(row=0, column=0)
        progress = 1
        progress_var = tk.DoubleVar()
        progress_bar = ttk.Progressbar(frame, orient="horizontal", length=300, variable=progress_var,
                                       maximum=np.count_nonzero(self.tile_colors))
        progress_bar.grid(row=1, column=0, padx=10, pady=10)
        window.pack_slaves()
        for iy in range(self.num_y_tiles):
            for ix in range(self.num_x_tiles):
                tile_label = self.tile_colors[ix, iy]
                if tile_label != 0:
                    if not os.path.exists("Curated_Images/" + str(int(tile_label) - 1)):
                        os.mkdir("Curated_Images/" + str(int(tile_label) - 1))
                    x, y = ix * self.orig_x_tile, iy * self.orig_y_tile
                    tile = Image.fromarray(self.orig_image[y:y + 128, x:x + 128])
                    tile_number = int(iy * self.num_x_tiles + ix)
                    tile.save("Curated_Images/" + str(int(tile_label) - 1) + "/" + os.path.splitext(self.filename)[0]
                              + '_tile' + str(tile_number) + '.png')
                    window.update()
                    progress += 1
                    progress_var.set(progress)
        window.destroy()
        tk.messagebox.showinfo("", "Tiles successfully generated.")

    def clear_grid(self):
        """Reset the grid"""
        self.image = Image.fromarray(self.orig_image)
        self.reference_image = self.orig_image
        self.show_image()
        self.tile_colors = np.zeros((self.num_x_tiles, self.num_y_tiles))


path = "Microscope_Images/image0192.tif"  # place path to your image here
root = tk.Tk()
app = ZoomAdvanced(root, path=path)
root.mainloop()
