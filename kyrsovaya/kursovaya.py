import tkinter as tk
from tkinter import messagebox, ttk
from tkcalendar import Calendar
import datetime
import pyodbc
import winsound
from pystray import Icon, MenuItem, Menu
from PIL import Image, ImageDraw
import threading

class ReminderApp:
    def __init__(self, root):
        self.root = root
        self.root.protocol("WM_DELETE_WINDOW", self.hide_window)  
        self.root.title("Календар з нагадуваннями")
        self.root.geometry("600x700")
        self.root.resizable(False, False)
        self.is_dark_mode = False

        try:
            self.conn = pyodbc.connect('DRIVER={ODBC Driver 17 for SQL Server};'
                                       'SERVER=DESKTOP-QQAOEK4;'  
                                       'DATABASE=Calendar;'        
                                       'Trusted_Connection=yes;'   
                                       'Encrypt=yes;'              
                                       'TrustServerCertificate=yes;')  
            self.cursor = self.conn.cursor()  
            print("З'єднання з базою даних встановлено успішно.")
        except pyodbc.Error as e:
            messagebox.showerror("Помилка підключення", f"Не вдалось підключитись до бази даних: {e}")
            self.root.quit()  

        self.create_table()

        self.root.configure(bg="#d4e8d4") 

        header = tk.Label(root, text="📅 Мій Календар", font=("Helvetica", 20, "bold"), bg="#4CAF50", fg="white")
        header.pack(fill="x", pady=10)

        self.cal_frame = tk.Frame(root, bg="#d4e8d4")
        self.cal_frame.pack(pady=10)
        self.cal = Calendar(
            self.cal_frame, 
            selectmode="day", 
            date_pattern="yyyy-mm-dd",
            locale="uk",
            background="lightblue", 
            foreground="black", 
            bordercolor="lightblue"
        )
        self.cal.pack()

        self.today_date = datetime.date.today()
        self.cal.calevent_create(self.today_date, "Сьогодні", "today")

        self.event_frame = tk.Frame(root, bg="#d4e8d4")
        self.event_frame.pack(pady=10)

        self.event_label = tk.Label(self.event_frame, text="Опис події:", font=("Helvetica", 12), bg="#d4e8d4")
        self.event_label.grid(row=0, column=0, padx=5, pady=5)

        self.event_entry = ttk.Entry(self.event_frame, width=30, font=("Helvetica", 12))
        self.event_entry.grid(row=0, column=1, padx=5)
        self.event_entry.insert(0, "Введіть опис події")

        self.event_type_label = tk.Label(self.event_frame, text="Тип події:", font=("Helvetica", 12), bg="#d4e8d4")
        self.event_type_label.grid(row=1, column=0, padx=5, pady=5)

        self.event_type = ttk.Combobox(self.event_frame, values=["Звичайна", "Важлива", "Термінова"], font=("Helvetica", 12))
        self.event_type.grid(row=1, column=1, padx=5)
        self.event_type.set("Звичайна")

        self.button_frame = tk.Frame(root, bg="#d4e8d4")
        self.button_frame.pack(pady=10)

        self.add_button = ttk.Button(self.button_frame, text="➕ Додати подію", command=self.add_event)
        self.add_button.grid(row=0, column=0, padx=10, pady=5)

        self.show_button = ttk.Button(self.button_frame, text="📜 Показати події", command=self.show_events)
        self.show_button.grid(row=0, column=1, padx=10, pady=5)

        self.remove_button = ttk.Button(self.button_frame, text="❌ Видалити подію", command=self.remove_event)
        self.remove_button.grid(row=0, column=2, padx=10, pady=5)

        self.edit_button = ttk.Button(self.button_frame, text="✏️ Редагувати подію", command=self.edit_event)
        self.edit_button.grid(row=1, column=0, padx=10, pady=5)

        self.complete_button = ttk.Button(self.button_frame, text="✅ Завершити подію", command=self.complete_event)
        self.complete_button.grid(row=1, column=1, padx=10, pady=5)

        self.save_button = ttk.Button(self.button_frame, text="💾 Зберегти зміни", command=self.save_changes)
        self.save_button.grid(row=1, column=2, padx=10, pady=5)

        self.list_frame = tk.Frame(root, bg="#e6ffe6", bd=2, relief="groove")
        self.list_frame.pack(fill="both", expand=True, padx=10, pady=10)

        self.list_label = tk.Label(self.list_frame, text="Список подій:", bg="#e6ffe6", font=("Helvetica", 14))
        self.list_label.pack(anchor="nw", padx=5, pady=5)

        self.event_list = tk.Listbox(
            self.list_frame, 
            font=("Helvetica", 12), 
            bg="#f9fff9",  
            selectbackground="#b3ffb3",  
            selectforeground="black", 
            height=10
        )
        self.event_list.pack(fill="both", expand=True, padx=5, pady=5)

        self.root.after(1000, self.daily_check)

    def create_table(self):
        self.cursor.execute(""" 
        IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='Events' AND xtype='U')
        CREATE TABLE Events (
            id INT PRIMARY KEY IDENTITY(1,1),
            event_date DATE,
            event_description NVARCHAR(255),
            event_type NVARCHAR(50),
            completed BIT
        )
        """)
        self.conn.commit()

    def add_event(self):
        date = self.cal.get_date()
        event = self.event_entry.get()
        event_type = self.event_type.get()

        if date and event and event.strip() != "":
            self.cursor.execute(""" 
                INSERT INTO Events (event_date, event_description, event_type, completed) 
                VALUES (?, ?, ?, ?)
            """, (date, event, event_type, False))
            self.conn.commit()

            messagebox.showinfo("Успіх", f"Подія '{event}' додана на {date}!")
            self.event_entry.delete(0, tk.END)
            self.update_event_list()
        else:
            messagebox.showerror("Помилка", "Будь ласка, виберіть дату та введіть подію.")

    def show_events(self):
        date = self.cal.get_date()
        self.cursor.execute("SELECT event_description, event_type, completed FROM Events WHERE event_date = ?", (date,))
        events = self.cursor.fetchall()
        if events:
            event_details = "\n".join([f"{event[0]} ({event[1]}) {'✔️' if event[2] else '❌'}" for event in events])
            messagebox.showinfo("Події", f"Події на {date}:\n{event_details}")
        else:
            messagebox.showinfo("Події", f"На {date} немає подій.")

    def remove_event(self):
        selected_event = self.event_list.curselection()
        if selected_event:
            event_info = self.event_list.get(selected_event)
            date = event_info.split(":")[0].strip()
            event_name = event_info.split(":")[1].split("(")[0].strip()

            self.cursor.execute("DELETE FROM Events WHERE event_date = ? AND event_description = ?", (date, event_name))
            self.conn.commit()

            self.update_event_list()
            messagebox.showinfo("Успіх", f"Подія '{event_name}' була видалена.")
        else:
            messagebox.showerror("Помилка", "Будь ласка, виберіть подію для видалення.")

    def update_event_list(self):
        self.event_list.delete(0, tk.END)
        self.cursor.execute("SELECT event_date, event_description, event_type, completed FROM Events ORDER BY event_date")
        events = self.cursor.fetchall()
        for event in events:
            date, description, event_type, completed = event
            color = "lightgreen" if event_type == "Звичайна" else "yellow" if event_type == "Важлива" else "red" 
            self.event_list.insert(tk.END, f"{date}: {description} ({event_type}) {'✔️' if completed else '❌'}")
            self.event_list.itemconfig(tk.END, {'bg': color})

    def edit_event(self):
        selected_event = self.event_list.curselection()
        if selected_event:
            event_info = self.event_list.get(selected_event)
            description = event_info.split(":")[1].split("(")[0].strip()  
            event_type = event_info.split("(")[1].split(")")[0].strip()  

            self.event_entry.delete(0, tk.END)
            self.event_entry.insert(0, description)  
            self.event_type.set(event_type)  

            self.selected_event = event_info  
        else:
            messagebox.showerror("Помилка", "Будь ласка, виберіть подію для редагування.")

    def save_changes(self):
        new_description = self.event_entry.get()
        new_event_type = self.event_type.get()

        if hasattr(self, 'selected_event') and self.selected_event:
            old_description = self.selected_event.split(":")[1].split("(")[0].strip()
            old_event_type = self.selected_event.split("(")[1].split(")")[0].strip()
            date = self.selected_event.split(":")[0].strip()

            if new_description != old_description or new_event_type != old_event_type:
                self.cursor.execute("UPDATE Events SET event_description = ?, event_type = ? WHERE event_date = ? AND event_description = ?",
                                    (new_description, new_event_type, date, old_description))
                self.conn.commit()

                self.update_event_list()
                messagebox.showinfo("Успіх", f"Подія успішно оновлена!")
            else:
                messagebox.showinfo("Інформація", "Опис події та тип не змінились.")
        else:
            messagebox.showerror("Помилка", "Будь ласка, спочатку виберіть подію для редагування.")

    def complete_event(self):
        selected_event = self.event_list.curselection()
        if selected_event:
            event_info = self.event_list.get(selected_event)
            date = event_info.split(":")[0].strip()
            event_name = event_info.split(":")[1].split("(")[0].strip()

            self.cursor.execute("UPDATE Events SET completed = 1 WHERE event_date = ? AND event_description = ?", (date, event_name))
            self.conn.commit()

            self.update_event_list()
            messagebox.showinfo("Успіх", f"Подія '{event_name}' була позначена як завершена.")
        else:
            messagebox.showerror("Помилка", "Будь ласка, виберіть подію для завершення.")

    def daily_check(self):
        today = datetime.date.today()
        self.cursor.execute("SELECT event_description FROM Events WHERE event_date = ? AND completed = 0", (today,))
        events = self.cursor.fetchall()
        for event in events:
            messagebox.showinfo("Нагадування", f"Сьогодні: {event[0]}")

        self.root.after(86400000, self.daily_check)

    def hide_window(self):
        self.root.withdraw()  

        icon = self.create_icon()
        icon.run()

    def create_icon(self):
        try:
            icon_image = Image.open("C:/Users/Ruslan Ostrovsky/Desktop/kyrsovaya/иконки/icon1.png")
            icon_image = icon_image.resize((64, 64))  
        except Exception as e:
            messagebox.showerror("Помилка", f"Не вдалось завантажити іконку: {e}")
            return None

        icon = Icon("ReminderApp", icon_image, menu=Menu(
            MenuItem("Показати", self.show_window),
            MenuItem("Вийти", self.quit_app)
        ))

        icon.tooltip = "Нагадування"
        return icon

    def show_window(self, icon):
        self.root.deiconify()  
        icon.stop()  

    def quit_app(self, icon):
        self.conn.close()  
        icon.stop()  
        self.root.quit()  

if __name__ == "__main__":
    root = tk.Tk()
    app = ReminderApp(root)
    root.mainloop()