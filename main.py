import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from PIL import Image, ImageTk
import fitz  # PyMuPDF
import os

class PDFSignerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("PDF Signature Tool")
        self.pdf_path = None
        self.signature_path = None
        self.signature_img = None
        self.signature_tk = None
        self.signature_on_canvas = None
        self.scale = 0.2
        self.offset_x = 400
        self.offset_y = 700
        self.page_count = 0
        self.selected_page = 1

        # Top toolbar
        toolbar = tk.Frame(root)
        toolbar.pack(side=tk.TOP, anchor="w", fill=tk.X, pady=4)

        btn_saveas = tk.Button(toolbar, text="Save As PDF", command=self.save_as_pdf)
        btn_saveas.pack(side=tk.LEFT, padx=4)

        btn_loadpdf = tk.Button(toolbar, text="Select PDF", command=self.load_pdf)
        btn_loadpdf.pack(side=tk.LEFT, padx=4)

        btn_loadsig = tk.Button(toolbar, text="Select Signature Image", command=self.load_signature)
        btn_loadsig.pack(side=tk.LEFT, padx=4)

        tk.Label(toolbar, text="Page:").pack(side=tk.LEFT, padx=(20,2))
        self.page_var = tk.IntVar(value=1)
        self.page_select = ttk.Combobox(toolbar, textvariable=self.page_var, width=5, state="readonly")
        self.page_select.pack(side=tk.LEFT)
        self.page_select.bind("<<ComboboxSelected>>", self.change_page)

        # Canvas with scrollbars
        canvas_frame = tk.Frame(root)
        canvas_frame.pack(fill=tk.BOTH, expand=True)

        self.canvas = tk.Canvas(canvas_frame, bg="gray")
        self.canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        vbar = tk.Scrollbar(canvas_frame, orient=tk.VERTICAL, command=self.canvas.yview)
        vbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.canvas.config(yscrollcommand=vbar.set)

        hbar = tk.Scrollbar(canvas_frame, orient=tk.HORIZONTAL, command=self.canvas.xview)
        hbar.pack(side=tk.BOTTOM, fill=tk.X)
        self.canvas.config(xscrollcommand=hbar.set)

        # 拖动和缩放
        self.canvas.bind("<B1-Motion>", self.move_signature)
        self.canvas.bind("<ButtonRelease-1>", self.reset_mouse)
        self.canvas.bind("<MouseWheel>", self.zoom_signature)
        self.last_mouse_pos = None

        self.root.bind("<Delete>", self.delete_signature)

    def load_pdf(self):
        self.pdf_path = filedialog.askopenfilename(filetypes=[("PDF Files", "*.pdf")])
        if self.pdf_path:
            doc = fitz.open(self.pdf_path)
            self.page_count = doc.page_count
            doc.close()
            self.page_select["values"] = list(range(1, self.page_count + 1))
            self.page_var.set(1)
            self.selected_page = 1
            self.show_pdf_preview()

    def load_signature(self):
        self.signature_path = filedialog.askopenfilename(filetypes=[("Image Files", "*.png;*.jpg;*.jpeg")])
        if self.signature_path:
            self.signature_img = Image.open(self.signature_path)
            self.signature_img = self.remove_white_bg(self.signature_img)
            self.scale = 0.2
            w, h = self.signature_img.size
            new_w = int(w * self.scale)
            new_h = int(h * self.scale)
            canvas_w = getattr(self, "current_canvas_w", 600)
            canvas_h = getattr(self, "current_canvas_h", 800)
            self.offset_x = (canvas_w - new_w) // 2
            self.offset_y = (canvas_h - new_h) // 2
            self.show_pdf_preview()

    def change_page(self, event=None):
        self.selected_page = self.page_var.get()
        self.show_pdf_preview()

    def show_pdf_preview(self):
        self.canvas.delete("all")
        if not self.pdf_path:
            return
        doc = fitz.open(self.pdf_path)
        page = doc[self.selected_page - 1]
        page_rect = page.rect
        doc.close()

        # 固定canvas宽度，按PDF比例调整高度
        canvas_w = 600
        canvas_h = int(canvas_w * page_rect.height / page_rect.width)
        self.canvas.config(width=canvas_w, height=canvas_h)

        # 渲染PDF页面为图片，缩放到canvas大小
        zoom = canvas_w / page_rect.width
        doc = fitz.open(self.pdf_path)
        page = doc[self.selected_page - 1]
        pix = page.get_pixmap(matrix=fitz.Matrix(zoom, zoom))
        img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
        self.pdf_preview = ImageTk.PhotoImage(img)
        self.canvas.create_image(0, 0, anchor="nw", image=self.pdf_preview)
        self.canvas.config(scrollregion=(0, 0, canvas_w, canvas_h))
        if self.signature_img:
            self.draw_signature_on_canvas()
        doc.close()
        # 记录canvas和PDF页面尺寸
        self.current_canvas_w = canvas_w
        self.current_canvas_h = canvas_h
        self.current_page_rect = page_rect
        self.current_zoom = zoom

    def draw_signature_on_canvas(self):
        if not self.signature_img:
            return
        # 缩放签名
        w, h = self.signature_img.size
        new_w = int(w * self.scale)
        new_h = int(h * self.scale)
        resized = self.signature_img.resize((new_w, new_h), Image.Resampling.LANCZOS)
        self.signature_tk = ImageTk.PhotoImage(resized)
        if self.signature_on_canvas:
            self.canvas.delete(self.signature_on_canvas)
        self.signature_on_canvas = self.canvas.create_image(
            self.offset_x, self.offset_y, anchor="nw", image=self.signature_tk
        )

    def move_signature(self, event):
        if not self.signature_img:
            return
        if self.last_mouse_pos:
            dx = event.x - self.last_mouse_pos[0]
            dy = event.y - self.last_mouse_pos[1]
            self.offset_x += dx
            self.offset_y += dy
            self.show_pdf_preview()
        self.last_mouse_pos = (event.x, event.y)

    def reset_mouse(self, event):
        self.last_mouse_pos = None

    def zoom_signature(self, event):
        if not self.signature_img:
            return
        if event.delta > 0:
            self.scale *= 1.1
        else:
            self.scale /= 1.1
        self.show_pdf_preview()

    def delete_signature(self, event=None):
        self.signature_img = None
        self.signature_tk = None
        self.signature_on_canvas = None
        self.show_pdf_preview()

    def save_as_pdf(self):
        if not self.pdf_path:
            messagebox.showerror("Error", "Please select a PDF file first.")
            return
        output_path = filedialog.asksaveasfilename(defaultextension=".pdf", filetypes=[("PDF Files", "*.pdf")])
        if not output_path:
            return

        doc = fitz.open(self.pdf_path)
        if self.signature_img:
            page = doc[self.selected_page - 1]
            page_rect = page.rect
            canvas_w = self.current_canvas_w
            canvas_h = self.current_canvas_h

            # 关键：canvas坐标→PDF页面坐标
            x_scale = page_rect.width / canvas_w
            y_scale = page_rect.height / canvas_h

            sig_w = self.signature_img.width * self.scale
            sig_h = self.signature_img.height * self.scale
            x0 = self.offset_x * x_scale
            y0 = self.offset_y * y_scale
            x1 = x0 + sig_w * x_scale
            y1 = y0 + sig_h * y_scale

            temp_sig = "temp_signature.png"
            self.signature_img.resize((int(sig_w), int(sig_h)), Image.Resampling.LANCZOS).save(temp_sig)
            page.insert_image([x0, y0, x1, y1], filename=temp_sig)
            os.remove(temp_sig)
        doc.save(output_path)
        doc.close()
        messagebox.showinfo("Done", f"Saved as {output_path}")

    def remove_white_bg(self, img, threshold=200):
        img = img.convert("RGBA")
        datas = img.getdata()
        newData = []
        for item in datas:
            if item[0] > threshold and item[1] > threshold and item[2] > threshold:
                newData.append((255, 255, 255, 0))
            else:
                newData.append(item)
        img.putdata(newData)
        return img

if __name__ == "__main__":
    root = tk.Tk()
    app = PDFSignerApp(root)
    root.mainloop()