import tkinter as tk
from tkinter import filedialog, messagebox
from pathlib import Path
import conciliador


def seleccionar_pdf():
    ruta = filedialog.askopenfilename(filetypes=[("PDF", "*.pdf"), ("Todos los archivos", "*.*")])
    if ruta:
        pdf_var.set(ruta)


def seleccionar_excel():
    ruta = filedialog.askopenfilename(filetypes=[("Excel", "*.xlsx;*.xls"), ("Todos los archivos", "*.*")])
    if ruta:
        excel_var.set(ruta)


def ejecutar_conciliacion():
    pdf = pdf_var.get()
    excel = excel_var.get()
    if not pdf or not excel:
        messagebox.showerror("Error", "Debes seleccionar ambos archivos")
        return
    try:
        df_banco = conciliador.leer_pdf(Path(pdf))
        df_conta = conciliador.leer_excel(Path(excel))
        df_banco, df_conta = conciliador.normalizar_datos(df_banco, df_conta)
        df = conciliador.conciliar(df_banco, df_conta)
        conciliador.generar_salida(df)
        messagebox.showinfo("Exito", "Conciliacion completada")
    except Exception as e:
        messagebox.showerror("Error", str(e))


root = tk.Tk()
root.title("Conciliador")

pdf_var = tk.StringVar()
excel_var = tk.StringVar()

frame = tk.Frame(root, padx=10, pady=10)
frame.pack()

# PDF
pdf_label = tk.Label(frame, text="PDF:")
pdf_label.grid(row=0, column=0, sticky="e")

pdf_entry = tk.Entry(frame, textvariable=pdf_var, width=40)
pdf_entry.grid(row=0, column=1)

pdf_button = tk.Button(frame, text="Seleccionar", command=seleccionar_pdf)
pdf_button.grid(row=0, column=2, padx=5)

# Excel
excel_label = tk.Label(frame, text="Excel:")
excel_label.grid(row=1, column=0, sticky="e")

excel_entry = tk.Entry(frame, textvariable=excel_var, width=40)
excel_entry.grid(row=1, column=1)

excel_button = tk.Button(frame, text="Seleccionar", command=seleccionar_excel)
excel_button.grid(row=1, column=2, padx=5)

# Conciliar button
conciliar_button = tk.Button(frame, text="Conciliar", command=ejecutar_conciliacion)
conciliar_button.grid(row=2, columnspan=3, pady=10)

root.mainloop()
