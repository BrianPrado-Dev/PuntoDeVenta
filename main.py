"""
Punto de Venta (POS) — Tortas Susy
Flet 0.84+ | SQLite3 | JSON | OOP
"""
import flet as ft
import sqlite3, json, os, copy
from datetime import datetime

try:
    import win32print
    WIN32_AVAILABLE = True
except ImportError:
    WIN32_AVAILABLE = False

try:
    import winsound
    WINSOUND_AVAILABLE = True
except ImportError:
    WINSOUND_AVAILABLE = False

DB_PATH = "clientes.db"
PEDIDOS_PATH = "pedidos_dia.json"

MENU = {
    "Comida": [("Torta",60),("Taco Dorado",10),("Taco c/Carne",25),("Kilo de Carne",300)],
    "Paquetes": [("Paquete #1",90),("Paquete #2",95),("Paquete #3",220),("Paquete #4",345),("Paquete #5",680)],
    "Bebidas": [("Refresco",30),("Cerveza",25),("Agua Fresca 500ml",15),("Agua Fresca 1LT",25)],
}
GRID_COLORS = {"Comida":"#2d3a5e","Paquetes":"#3b2d5e","Bebidas":"#1e4d3a"}

BG_DARK="#1a1a2e"; BG_CARD="#16213e"; ACCENT="#e94560"
ACCENT2="#533483"; TXT="#eaeaea"; GREEN="#00b894"; GOLD="#fdcb6e"
ERROR_RED="#d63031"

def play_notification_sound(kind: str):
    if not WINSOUND_AVAILABLE:
        return
    if kind=="print_success":
        winsound.MessageBeep(winsound.MB_OK)
    elif kind=="print_error":
        winsound.MessageBeep(winsound.MB_ICONHAND)
    elif kind=="clean_success":
        winsound.MessageBeep(winsound.MB_ICONASTERISK)
    elif kind=="list_click":
        winsound.Beep(1200, 45)
    else:
        winsound.Beep(900, 45)

# ─── DB ───
def init_db():
    c=sqlite3.connect(DB_PATH); c.execute(
        "CREATE TABLE IF NOT EXISTS clientes(telefono TEXT PRIMARY KEY,usuario TEXT,domicilio TEXT,cruces TEXT)"
    ); c.commit(); c.close()

def buscar_cliente(tel):
    c=sqlite3.connect(DB_PATH); r=c.execute(
        "SELECT domicilio,cruces FROM clientes WHERE telefono=?",(tel,)
    ).fetchone(); c.close(); return r

def guardar_cliente(tel,dom,cru):
    c=sqlite3.connect(DB_PATH); c.execute(
        "INSERT OR REPLACE INTO clientes(telefono,usuario,domicilio,cruces) VALUES(?,?,?,?)",
        (tel,"",dom,cru)); c.commit(); c.close()

# ─── JSON ───
def cargar_pedidos():
    if not os.path.exists(PEDIDOS_PATH): return []
    with open(PEDIDOS_PATH,"r",encoding="utf-8") as f:
        try: return json.load(f)
        except: return []

def guardar_pedido(p):
    ps=cargar_pedidos(); ps.append(p)
    with open(PEDIDOS_PATH,"w",encoding="utf-8") as f:
        json.dump(ps,f,ensure_ascii=False,indent=2)

# ─── Ticket 25 chars ───
def wrap(t,mx=25):
    ws=t.split(); ls=[]; cur=""
    for w in ws:
        if len(w)>mx:
            if cur: ls.append(cur); cur=""
            while len(w)>mx: ls.append(w[:mx]); w=w[mx:]
            if w: cur=w
        elif not cur: cur=w
        elif len(cur)+1+len(w)<=mx: cur+=" "+w
        else: ls.append(cur); cur=w
    if cur: ls.append(cur)
    return "\n".join(ls)

def generar_ticket_impresion(ped):
    s="="*25; t=[wrap("TORTAS SUSY"),s,wrap(f"Fecha: {ped.get('fecha','')}"),wrap(f"Hora: {ped.get('hora','')}"),s]
    for l,k in [("Tel","telefono"),("Dom","domicilio"),("Cruces","cruces"),("Hr esp","hora_especifica")]:
        v=ped.get(k,"")
        if v: t.append(wrap(f"{l}: {v}"))
    t+=[s,wrap("PEDIDO:"),"-"*25]
    for pl in ped.get("platos",[]):
        t.append(wrap(f"-- {pl['nombre']} --"))
        for it in pl.get("items",[]):
            t.append(wrap(f"{it['qty']}x {it['name']} ${it['price']*it['qty']}"))
    t+=[s,wrap(f"TOTAL: ${ped.get('total',0)}"),s,wrap("Gracias por su compra!"),"\n\n\n"]
    return "\n".join(t)


# ═══════════════════════════════════════
#  IMPRESORA FÍSICA (win32print)
# ═══════════════════════════════════════
class TicketPrinter:
    """Gestiona la impresión física en impresora térmica vía win32print."""
    def __init__(self):
        self.printer_name = None
        if WIN32_AVAILABLE:
            try:
                self.printer_name = win32print.GetDefaultPrinter()
            except Exception:
                self.printer_name = None

    def imprimir(self, ticket_text: str) -> tuple[bool, str]:
        """Envía el ticket a la impresora. Retorna (éxito, mensaje)."""
        if not WIN32_AVAILABLE:
            return False, "win32print no disponible (pywin32 no instalado)"
        if not self.printer_name:
            return False, "No se detectó impresora por defecto"
        try:
            hprinter = win32print.OpenPrinter(self.printer_name)
            try:
                win32print.StartDocPrinter(hprinter, 1, ("Ticket POS", None, "RAW"))
                win32print.StartPagePrinter(hprinter)
                win32print.WritePrinter(hprinter, ticket_text.encode("utf-8"))
                win32print.EndPagePrinter(hprinter)
                win32print.EndDocPrinter(hprinter)
            finally:
                win32print.ClosePrinter(hprinter)
            return True, "Ticket enviado a impresora"
        except Exception as ex:
            return False, f"Error al imprimir: {ex}"

# Instancia global de impresora
printer = TicketPrinter()

# ═══════════════════════════════════════
#  DATA MODELS
# ═══════════════════════════════════════
class Plato:
    _n=0
    def __init__(self,nombre=None,items=None):
        if nombre is None: Plato._n+=1; nombre=f"Plato {Plato._n}"
        self.nombre=nombre; self.items=items or []
    def agregar(self,name,price):
        for i in self.items:
            if i["name"]==name: i["qty"]+=1; return
        self.items.append({"name":name,"price":price,"qty":1})
    def total(self): return sum(i["price"]*i["qty"] for i in self.items)
    def to_dict(self): return {"nombre":self.nombre,"items":[dict(i) for i in self.items]}
    def clonar(self):
        Plato._n+=1; return Plato(f"Plato {Plato._n}",copy.deepcopy(self.items))

class PedidoState:
    def __init__(self):
        self.platos:list[Plato]=[]; self.activo=-1; self.cli_existe=False; Plato._n=0
    def crear_plato(self):
        p=Plato(); self.platos.append(p); self.activo=len(self.platos)-1; return p
    def eliminar(self,i):
        if 0<=i<len(self.platos):
            self.platos.pop(i)
            if self.activo>=len(self.platos): self.activo=len(self.platos)-1
    def duplicar(self,i):
        if 0<=i<len(self.platos): self.platos.insert(i+1,self.platos[i].clonar())
    def agregar_a_activo(self,name,price):
        if 0<=self.activo<len(self.platos): self.platos[self.activo].agregar(name,price); return True
        return False
    def mover_item(self,sp,si,dp):
        if sp==dp: return
        src=self.platos[sp]; item=src.items.pop(si)
        dst=self.platos[dp]
        for i in dst.items:
            if i["name"]==item["name"]: i["qty"]+=item["qty"]; return
        dst.items.append(item)
    def total(self): return sum(p.total() for p in self.platos)
    def limpiar(self): self.platos.clear(); self.activo=-1; Plato._n=0; self.cli_existe=False

# ═══════════════════════════════════════
#  UI COMPONENTS
# ═══════════════════════════════════════
class FormularioCliente:
    def __init__(self,page,state):
        self.page=page; self.state=state
        ts=dict(dense=True,border_color=ACCENT2,color=TXT,text_size=13,height=40)
        self.tf_dom=ft.TextField(width=200,**ts)
        self.tf_cru=ft.TextField(width=200,**ts)
        self.tf_tel=ft.TextField(width=150,on_blur=self._buscar,on_submit=self._buscar,**ts)
        # Segmented buttons
        self.seg_tel=ft.SegmentedButton(
            segments=[ft.Segment(value="si",label=ft.Text("Sí")),ft.Segment(value="no",label=ft.Text("No"))],
            selected=["si"],on_change=self._toggle_tel,allow_empty_selection=False)
        self.seg_hora=ft.SegmentedButton(
            segments=[ft.Segment(value="si",label=ft.Text("Sí")),ft.Segment(value="no",label=ft.Text("No"))],
            selected=["no"],on_change=self._toggle_hora,allow_empty_selection=False)
        # Hour dropdowns
        self.dd_h=ft.Dropdown(width=75,options=[ft.DropdownOption(key=str(i),text=str(i)) for i in range(1,13)],
                              value="12",dense=True,disabled=True,text_size=13)
        self.dd_m=ft.Dropdown(width=75,options=[ft.DropdownOption(key=f"{i:02d}",text=f"{i:02d}") for i in range(0,60,10)],
                              value="00",dense=True,disabled=True,text_size=13)
        self.dd_p=ft.Dropdown(width=80,options=[ft.DropdownOption(key="AM",text="AM"),ft.DropdownOption(key="PM",text="PM")],
                              value="PM",dense=True,disabled=True,text_size=13)

    def _buscar(self,e):
        tel=self.tf_tel.value.strip()
        if not tel: return
        r=buscar_cliente(tel)
        if r: self.tf_dom.value,self.tf_cru.value=r; self.state.cli_existe=True
        else: self.state.cli_existe=False
        self.page.update()

    def _toggle_tel(self,e):
        off="no" in self.seg_tel.selected
        self.tf_tel.disabled=off; self.page.update()

    def _toggle_hora(self,e):
        off="no" in self.seg_hora.selected
        self.dd_h.disabled=off; self.dd_m.disabled=off; self.dd_p.disabled=off; self.page.update()

    def get_hora_str(self):
        if "no" in self.seg_hora.selected: return ""
        return f"{self.dd_h.value}:{self.dd_m.value} {self.dd_p.value}"

    def get_tel(self):
        if "no" in self.seg_tel.selected: return ""
        return self.tf_tel.value.strip()

    def limpiar(self):
        self.tf_dom.value=""; self.tf_cru.value=""; self.tf_tel.value=""
        self.seg_tel.selected=["si"]; self.seg_hora.selected=["no"]
        self.tf_tel.disabled=False
        self.dd_h.disabled=True; self.dd_m.disabled=True; self.dd_p.disabled=True
        self.dd_h.value="12"; self.dd_m.value="00"; self.dd_p.value="PM"

    def build(self):
        lbl=lambda t: ft.Text(t,color=GOLD,size=13,weight=ft.FontWeight.BOLD)
        return ft.Container(
            content=ft.Column([
                ft.Text("📝 Datos del cliente",size=14,weight=ft.FontWeight.BOLD,color=GOLD),
                ft.Row([lbl("Domicilio:"),self.tf_dom],spacing=5,vertical_alignment=ft.CrossAxisAlignment.CENTER),
                ft.Row([lbl("Cruces:"),self.tf_cru],spacing=5,vertical_alignment=ft.CrossAxisAlignment.CENTER),
                ft.Row([lbl("Teléfono:"),self.seg_tel,self.tf_tel],spacing=5,vertical_alignment=ft.CrossAxisAlignment.CENTER),
                ft.Row([lbl("Hora:"),self.seg_hora,self.dd_h,self.dd_m,self.dd_p],
                       spacing=5,vertical_alignment=ft.CrossAxisAlignment.CENTER),
            ],spacing=8),bgcolor=BG_CARD,border_radius=10,padding=12)


class MenuProductos:
    def __init__(self,on_product_click):
        self.on_click=on_product_click

    def _card(self,name,price,color):
        return ft.Container(
            content=ft.Column([
                ft.Text(name,size=13,weight=ft.FontWeight.BOLD,color=TXT,text_align=ft.TextAlign.CENTER),
                ft.Text(f"${price}",size=17,weight=ft.FontWeight.W_900,color=GOLD,text_align=ft.TextAlign.CENTER),
            ],alignment=ft.MainAxisAlignment.CENTER,horizontal_alignment=ft.CrossAxisAlignment.CENTER,spacing=3),
            width=130,height=75,bgcolor=color,border_radius=12,alignment=ft.Alignment(0,0),
            on_click=lambda _,n=name,p=price: self.on_click(n,p),ink=True,
            shadow=ft.BoxShadow(spread_radius=1,blur_radius=6,color=ft.Colors.with_opacity(0.25,"black"),offset=ft.Offset(0,2)))

    def _grid(self,items,color):
        g=ft.GridView(runs_count=3,max_extent=150,child_aspect_ratio=1.7,spacing=8,run_spacing=8,padding=8,expand=True)
        for n,p in items: g.controls.append(self._card(n,p,color))
        return g

    def build(self):
        cats=list(MENU.keys())
        return ft.Tabs(
            content=ft.Column([
                ft.TabBar(tabs=[ft.Tab(label=f"{'🍔📦🥤'[i]} {c}") for i,c in enumerate(cats)],
                          indicator_color=ACCENT,label_color=GOLD,unselected_label_color=TXT),
                ft.TabBarView(controls=[self._grid(MENU[c],GRID_COLORS[c]) for c in cats],expand=True),
            ],expand=True),length=len(cats),selected_index=0,expand=True)


class ResumenPedido:
    """Panel derecho: selector de plato, resumen con drag & drop, total."""
    def __init__(self,page,state):
        self.page=page; self.state=state
        self._drag_map={}  # drag_key -> (plato_idx, item_idx)
        self.dd_plato=ft.Dropdown(label="Plato actual",dense=True,text_size=13,
                                  on_select=self._on_plato_change,expand=True,
                                  border_color=ACCENT2,color=TXT)
        self.lv=ft.ListView(expand=True,spacing=4,padding=5)
        self.txt_total=ft.Text("Total: $0",size=20,weight=ft.FontWeight.BOLD,color=GOLD,text_align=ft.TextAlign.CENTER)
        self._editing_idx=-1  # plato being renamed

    def _on_plato_change(self,e):
        v=self.dd_plato.value
        if v is not None and v.isdigit(): self.state.activo=int(v)

    def refresh(self):
        self._drag_map.clear(); self.lv.controls.clear()
        # Refresh dropdown
        self.dd_plato.options=[ft.DropdownOption(key=str(i),text=p.nombre) for i,p in enumerate(self.state.platos)]
        if 0<=self.state.activo<len(self.state.platos): self.dd_plato.value=str(self.state.activo)
        elif self.state.platos: self.dd_plato.value="0"; self.state.activo=0
        else: self.dd_plato.value=None

        for pi,plato in enumerate(self.state.platos):
            # Build items column
            items_col=ft.Column(spacing=2)
            for ii,item in enumerate(plato.items):
                dk=f"{pi}:{ii}"
                self._drag_map[dk]={"sp":pi,"si":ii}
                sub=item["price"]*item["qty"]
                item_row=ft.Container(
                    content=ft.Row([
                        ft.Icon(ft.Icons.DRAG_INDICATOR,color=ACCENT2,size=14),
                        ft.Text(f'{item["qty"]}x',color=ACCENT,weight=ft.FontWeight.BOLD,size=12),
                        ft.Text(item["name"],color=TXT,expand=True,size=12),
                        ft.Text(f'${sub}',color=GOLD,weight=ft.FontWeight.BOLD,size=12),
                        ft.IconButton(icon=ft.Icons.REMOVE_CIRCLE_OUTLINE,icon_color=ACCENT,icon_size=14,
                                      data=f"{pi}:{ii}",on_click=self._quitar,padding=0),
                    ]),bgcolor="#1e2a4a",border_radius=5,padding=ft.Padding(6,4,6,4))
                draggable=ft.Draggable(content=item_row,group="items",data=dk)
                items_col.controls.append(draggable)

            # Plato header
            if self._editing_idx==pi:
                name_ctl=ft.TextField(value=plato.nombre,dense=True,height=30,text_size=12,
                                      color=TXT,width=120,on_submit=lambda e,idx=pi: self._rename_done(e,idx))
            else:
                name_ctl=ft.Text(plato.nombre,color=GOLD,weight=ft.FontWeight.BOLD,size=13)

            header=ft.Row([
                name_ctl,ft.Row([
                    ft.IconButton(icon=ft.Icons.EDIT,icon_color=GOLD,icon_size=14,data=pi,on_click=self._edit_name,padding=0,tooltip="Renombrar"),
                    ft.IconButton(icon=ft.Icons.COPY,icon_color=GREEN,icon_size=14,data=pi,on_click=self._dup,padding=0,tooltip="Duplicar"),
                    ft.IconButton(icon=ft.Icons.DELETE,icon_color=ACCENT,icon_size=14,data=pi,on_click=self._del,padding=0,tooltip="Eliminar"),
                ],spacing=0)
            ],alignment=ft.MainAxisAlignment.SPACE_BETWEEN)

            plato_box=ft.Container(
                content=ft.Column([header,items_col],spacing=4),
                bgcolor="#111a30",border_radius=8,padding=8,
                margin=ft.Margin(bottom=6),
                border=ft.border.all(1,ACCENT2))

            target=ft.DragTarget(content=plato_box,group="items",data=str(pi),
                                  on_accept=self._on_drop,
                                  on_will_accept=self._on_will)
            self.lv.controls.append(target)

        self.txt_total.value=f"Total: ${self.state.total()}"
        self.page.update()

    def _on_will(self,e):
        e.control.content.border=ft.border.all(2,GREEN) if e.accept else ft.border.all(1,ACCENT2)
        self.page.update()

    def _on_drop(self,e):
        dst=int(e.control.data)
        src_data=e.src.data  # e.src is the Draggable object
        info=self._drag_map.get(src_data)
        if info is None: return
        self.state.mover_item(info["sp"],info["si"],dst)
        self.refresh()

    def _quitar(self,e):
        pi,ii=[int(x) for x in e.control.data.split(":")]
        pl=self.state.platos[pi]
        pl.items[ii]["qty"]-=1
        if pl.items[ii]["qty"]<=0: pl.items.pop(ii)
        self.refresh()

    def _edit_name(self,e):
        self._editing_idx=e.control.data; self.refresh()

    def _rename_done(self,e,idx):
        self.state.platos[idx].nombre=e.control.value; self._editing_idx=-1; self.refresh()

    def _dup(self,e):
        self.state.duplicar(e.control.data); self.refresh()

    def _del(self,e):
        self.state.eliminar(e.control.data); self.refresh()

    def build(self):
        return ft.Container(
            content=ft.Column([
                ft.Text("🧾 Resumen del pedido",size=15,weight=ft.FontWeight.BOLD,color=GOLD,text_align=ft.TextAlign.CENTER),
                self.dd_plato,
                ft.Container(content=self.lv,expand=True,bgcolor="#0d1525",border_radius=8,padding=4),
                ft.Divider(color=ACCENT2,height=1),
                ft.Container(content=self.txt_total,alignment=ft.Alignment(0,0),padding=8),
            ],expand=True),
            expand=5,bgcolor=BG_CARD,border_radius=12,padding=10,
            shadow=ft.BoxShadow(spread_radius=1,blur_radius=10,color=ft.Colors.with_opacity(0.35,"black"),offset=ft.Offset(0,3)))


class HistorialDialog:
    def __init__(self,page):
        self.page=page

    def _mostrar_estado_impresion(self, ok: bool):
        txt = "Impresion Exitosa" if ok else "Error de impresion"
        bg = GREEN if ok else ERROR_RED
        self.page.snack_bar=ft.SnackBar(ft.Text(txt,color="white"),bgcolor=bg)
        self.page.snack_bar.open=True
        self.page.update()

    def _pedido_card(self,p):
        # Client info lines
        info=[]
        if p.get("domicilio"): info.append(f"📍 {p['domicilio']}")
        if p.get("cruces"): info.append(f"🔀 {p['cruces']}")
        if p.get("telefono"): info.append(f"📞 {p['telefono']}")
        hora_especifica = p.get("hora_especifica","")

        def reimprimir(_e,ped=p):
            ticket=generar_ticket_impresion(ped)
            print("\n"+ticket)
            ok,msg=printer.imprimir(ticket)
            play_notification_sound("print_success" if ok else "print_error")
            self._mostrar_estado_impresion(ok)

        return ft.Container(
            content=ft.Column([
                ft.Row([
                    ft.Container(expand=True),
                    ft.Text(
                        f"⏰ {hora_especifica}",
                        color=GOLD,
                        size=22,
                        weight=ft.FontWeight.W_900,
                        text_align=ft.TextAlign.RIGHT,
                    ) if hora_especifica else ft.Container(),
                ],alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                # Cliente info (destacado)
                *[ft.Text(line,color=TXT,size=12,weight=ft.FontWeight.BOLD) for line in info],
                ft.Divider(color=ACCENT2,height=1),
                # Items por plato (énfasis)
                *[ft.Container(
                    content=ft.Column([
                        ft.Text(pl['nombre'],color=ACCENT,size=11,weight=ft.FontWeight.BOLD),
                        *[ft.Text(f"  {it['qty']}x {it['name']}  ${it['price']*it['qty']}",
                                  color=GOLD,size=12,weight=ft.FontWeight.W_500)
                          for it in pl.get("items",[])],
                    ],spacing=1),padding=ft.Padding(0,2,0,2),
                ) for pl in p.get("platos",[])],
                ft.Divider(color=ACCENT2,height=1),
                # Total + hora + reimprimir
                ft.Row([
                    ft.Text(f"Total: ${p.get('total',0)}",color=GREEN,weight=ft.FontWeight.BOLD,size=13),
                    ft.Row([
                        ft.Text(p.get('hora',''),color="#666",size=10),
                        ft.IconButton(icon=ft.Icons.PRINT,icon_color=GREEN,icon_size=14,
                                      on_click=reimprimir,padding=0,tooltip="Reimprimir"),
                    ],spacing=2),
                ],alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
            ],spacing=3),bgcolor="#1e2a4a",border_radius=8,padding=10,margin=ft.Margin(bottom=5))

    def _build_column(self,titulo,pedidos):
        if not pedidos:
            lista=ft.Text("Sin pedidos.",color=TXT,size=13)
        else:
            lista=ft.ListView(
            controls=[self._pedido_card(p) for p in pedidos],
                expand=True)
        return ft.Container(
            content=ft.Column([
                ft.Text(titulo,size=14,weight=ft.FontWeight.BOLD,color=GOLD,
                        text_align=ft.TextAlign.CENTER),
                ft.Divider(color=ACCENT2,height=1),
                ft.Container(content=lista,expand=True),
            ],expand=True),
            expand=True,bgcolor="#111a30",border_radius=8,padding=8)

    def mostrar(self):
        pedidos=cargar_pedidos()
        con_hora=[p for p in pedidos if p.get("hora_especifica")]
        sin_hora=[p for p in pedidos if not p.get("hora_especifica")]

        content=ft.Row([
            self._build_column("🍽️ Sin hora",sin_hora),
            ft.VerticalDivider(color=ACCENT2,width=1),
            self._build_column("⏰ Con hora",con_hora),
        ],expand=True,spacing=8,height=420,width=700)

        dlg=ft.AlertDialog(title=ft.Text("📋 Pedidos del día",color=GOLD,weight=ft.FontWeight.BOLD),
                           content=content,bgcolor=BG_CARD)
        self.page.overlay.append(dlg); dlg.open=True; self.page.update()


# ═══════════════════════════════════════
#  MAIN
# ═══════════════════════════════════════
def main(page: ft.Page):
    page.title="Punto de Venta — Tortas Susy"
    page.bgcolor=BG_DARK; page.padding=10
    page.window.width=1150; page.window.height=750
    page.theme_mode=ft.ThemeMode.DARK
    init_db()

    state=PedidoState()
    form=FormularioCliente(page,state)
    resumen=ResumenPedido(page,state)
    historial=HistorialDialog(page)

    def mostrar_mensaje_estado(texto: str, ok: bool):
        page.snack_bar=ft.SnackBar(ft.Text(texto,color="white"),bgcolor=GREEN if ok else ERROR_RED)
        page.snack_bar.open=True
        page.update()

    def on_product(name,price):
        if not state.platos:
            state.crear_plato()
        if state.agregar_a_activo(name,price):
            resumen.refresh()
        else:
            page.snack_bar=ft.SnackBar(ft.Text("Selecciona un plato primero",color="white"),bgcolor=ACCENT)
            page.snack_bar.open=True; page.update()

    menu=MenuProductos(on_product)
    bs=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=8))

    def on_imprimir(_e):
        tel=form.get_tel()
        if tel and not state.cli_existe:
            guardar_cliente(tel,form.tf_dom.value.strip(),form.tf_cru.value.strip())
            state.cli_existe=True
        now=datetime.now()
        ped={"fecha":now.strftime("%Y-%m-%d"),"hora":now.strftime("%H:%M:%S"),
             "telefono":tel,"domicilio":form.tf_dom.value.strip(),"cruces":form.tf_cru.value.strip(),
             "hora_especifica":form.get_hora_str(),
             "platos":[p.to_dict() for p in state.platos],"total":state.total()}
        # Siempre guardar primero (JSON + SQLite)
        guardar_pedido(ped)
        ticket=generar_ticket_impresion(ped)
        print("\n"+ticket)  # Consola siempre
        # Intentar impresión física
        ok,msg=printer.imprimir(ticket)
        play_notification_sound("print_success" if ok else "print_error")
        mostrar_mensaje_estado("Impresion Exitosa" if ok else "Error de impresion",ok)

    def on_limpiar(_e):
        state.limpiar(); form.limpiar(); resumen.refresh()
        play_notification_sound("clean_success")
        mostrar_mensaje_estado("Limpiesa Exitosa",True)

    def on_crear_plato(_e):
        state.crear_plato(); resumen.refresh()

    def on_lista(_e):
        play_notification_sound("list_click")
        historial.mostrar()

    btns=ft.Column([
        ft.Row([
            ft.Button("🖨️ Imprimir",on_click=on_imprimir,bgcolor=GREEN,color="white",style=bs,height=36,expand=True),
            ft.Button("🗑️ Limpiar",on_click=on_limpiar,bgcolor=ACCENT,color="white",style=bs,height=36,expand=True),
        ],spacing=6),
        ft.Row([
            ft.Button("➕ Plato",on_click=on_crear_plato,bgcolor=ACCENT2,color="white",style=bs,height=36,expand=True),
            ft.Button("📋 Lista",on_click=on_lista,bgcolor="#2d3a5e",color="white",style=bs,height=36,expand=True),
        ],spacing=6),
    ],spacing=4)

    lado_izq=ft.Container(content=ft.Column([
        form.build(),ft.Container(content=menu.build(),expand=True),btns
    ],spacing=8,expand=True),expand=5)

    page.add(ft.Row([lado_izq,resumen.build()],expand=True,spacing=10))

if __name__=="__main__":
    ft.run(main)
