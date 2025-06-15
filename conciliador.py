import argparse
import pandas as pd
import pdfplumber
from pathlib import Path
from datetime import datetime


def parse_args():
    parser = argparse.ArgumentParser(description="Conciliar movimientos bancarios y contables")
    parser.add_argument("pdf", help="Ruta al estado de cuenta en PDF")
    parser.add_argument("excel", help="Ruta al extracto contable en Excel")
    return parser.parse_args()


def leer_pdf(ruta_pdf: Path) -> pd.DataFrame:
    registros = []
    try:
        with pdfplumber.open(ruta_pdf) as pdf:
            for page in pdf.pages:
                tablas = page.extract_tables()
                for tabla in tablas:
                    for fila in tabla:
                        if not fila or "FECHA" in fila[0] or "RESUMEN" in fila[0]:
                            continue
                        if any(pal in (fila[1] or "") for pal in ["SALDO PROMEDIO", "CUPO", "RETENCION"]):
                            continue
                        fecha, descripcion, sucursal, dcto, valor, saldo = fila[:6]
                        if not fecha or not valor:
                            continue
                        registros.append({
                            "fecha": fecha.strip(),
                            "descripcion": (descripcion or "").strip(),
                            "valor": valor,
                        })
    except Exception as e:
        raise RuntimeError(f"Error leyendo PDF: {e}")

    df = pd.DataFrame(registros)
    if df.empty:
        raise RuntimeError("No se encontraron transacciones en el PDF")
    return df


def leer_excel(ruta_excel: Path) -> pd.DataFrame:
    try:
        df = pd.read_excel(ruta_excel, engine="openpyxl")
    except Exception as e:
        raise RuntimeError(f"Error leyendo Excel: {e}")
    columnas = df.columns.str.lower()
    if not {"fecha", "detalle"}.issubset(columnas):
        raise RuntimeError("Faltan columnas obligatorias en el Excel")
    df.columns = columnas
    return df


def normalizar_datos(df_banco: pd.DataFrame, df_conta: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    df_banco = df_banco.copy()
    df_banco["fecha"] = df_banco["fecha"].apply(lambda x: datetime.strptime(f"{x}/2025", "%d/%m/%Y"))
    df_banco["valor_banco"] = df_banco["valor"].str.replace(".", "", regex=False).str.replace(",", ".")
    df_banco["valor_banco"] = df_banco["valor_banco"].str.replace(" ", "").astype(float)
    df_banco = df_banco.drop(columns=["valor"])

    df_conta = df_conta.copy()
    df_conta["fecha"] = pd.to_datetime(df_conta["fecha"], dayfirst=True, errors="coerce")
    df_conta["debito"] = df_conta.get("débitos") if "débitos" in df_conta.columns else df_conta.get("debitos")
    df_conta["credito"] = df_conta.get("créditos") if "créditos" in df_conta.columns else df_conta.get("creditos")
    for col in ["debito", "credito"]:
        if col not in df_conta:
            df_conta[col] = 0
    df_conta["debito"] = df_conta["debito"].fillna(0)
    df_conta["credito"] = df_conta["credito"].fillna(0)
    df_conta["debito"] = df_conta["debito"].astype(str).str.replace(".", "", regex=False).str.replace(",", ".")
    df_conta["credito"] = df_conta["credito"].astype(str).str.replace(".", "", regex=False).str.replace(",", ".")
    df_conta["debito"] = df_conta["debito"].str.replace(" ", "").astype(float)
    df_conta["credito"] = df_conta["credito"].str.replace(" ", "").astype(float)
    df_conta["valor_contable"] = df_conta["credito"] - df_conta["debito"]
    return df_banco, df_conta


def conciliar(df_banco: pd.DataFrame, df_conta: pd.DataFrame) -> pd.DataFrame:
    df_conta = df_conta.copy()
    df_conta["usado"] = False
    resultados = []

    for _, mov in df_banco.iterrows():
        fecha_b = mov["fecha"]
        val_b = mov["valor_banco"]
        match = df_conta[(~df_conta["usado"]) & (df_conta["fecha"] == fecha_b) & (df_conta["valor_contable"].abs() == abs(val_b))]
        estado = "OK"
        if match.empty:
            match = df_conta[(~df_conta["usado"]) & (df_conta["fecha"] == fecha_b) & (abs(df_conta["valor_contable"].abs() - abs(val_b)) <= 100)]
            estado = "Monto difiere"
        if match.empty:
            match = df_conta[(~df_conta["usado"]) & (df_conta["valor_contable"].abs() == abs(val_b)) & (abs((df_conta["fecha"] - fecha_b).dt.days) <= 1)]
            estado = "Fecha difiere"
        if not match.empty:
            idx = match.index[0]
            df_conta.loc[idx, "usado"] = True
            val_c = df_conta.loc[idx, "valor_contable"]
            resultados.append({
                "fecha_banco": fecha_b,
                "descripcion_banco": mov["descripcion"],
                "valor_banco": val_b,
                "fecha_conta": df_conta.loc[idx, "fecha"],
                "detalle_conta": df_conta.loc[idx, "detalle"],
                "valor_conta": val_c,
                "diferencia": val_b - val_c,
                "estado": estado,
            })
        else:
            resultados.append({
                "fecha_banco": fecha_b,
                "descripcion_banco": mov["descripcion"],
                "valor_banco": val_b,
                "fecha_conta": pd.NaT,
                "detalle_conta": None,
                "valor_conta": None,
                "diferencia": None,
                "estado": "Solo banco",
            })

    sobrantes = df_conta[~df_conta["usado"]]
    for _, mov in sobrantes.iterrows():
        resultados.append({
            "fecha_banco": pd.NaT,
            "descripcion_banco": None,
            "valor_banco": None,
            "fecha_conta": mov["fecha"],
            "detalle_conta": mov["detalle"],
            "valor_conta": mov["valor_contable"],
            "diferencia": None,
            "estado": "Solo contabilidad",
        })

    return pd.DataFrame(resultados)


def generar_salida(df: pd.DataFrame):
    coincidencias = df[df["estado"].isin(["OK", "Monto difiere", "Fecha difiere"])]
    pendientes = df[df["estado"].isin(["Solo banco", "Solo contabilidad"])]

    with pd.ExcelWriter("conciliacion_detalle.xlsx") as writer:
        coincidencias.to_excel(writer, sheet_name="coincidencias", index=False)
        pendientes.to_excel(writer, sheet_name="pendientes", index=False)

    resumen = df["estado"].value_counts().rename_axis("estado").reset_index(name="total")
    resumen.to_csv("conciliacion_resumen.csv", index=False)

    print("Resumen de conciliación:")
    print(resumen.to_string(index=False))


def main():
    args = parse_args()
    pdf_path = Path(args.pdf)
    excel_path = Path(args.excel)
    df_banco = leer_pdf(pdf_path)
    df_conta = leer_excel(excel_path)
    df_banco, df_conta = normalizar_datos(df_banco, df_conta)
    df = conciliar(df_banco, df_conta)
    generar_salida(df)


if __name__ == "__main__":
    main()
