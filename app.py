import flet as ft
from datetime import datetime
import requests
from escpos.printer import Usb
import time

months_in_spanish = {
    "January": "Enero",
    "February": "Febrero",
    "March": "Marzo",
    "April": "Abril",
    "May": "Mayo",
    "June": "Junio",
    "July": "Julio",
    "August": "Agosto",
    "September": "Septiembre",
    "October": "Octubre",
    "November": "Noviembre",
    "December": "Diciembre"
}

class ApplicationState:
    def __init__(self):
        self.previous_pending_count = 0
        self.currentOrder = None
        self.currentId = 1
        self.orderArray = []
        self.detailsToPrint = []
        self.orderToPrint = None
        self.run_query = True
        self.modal_open = False

app_state = ApplicationState()

class OrderInfo():
    def __init__(self, id: str, name: str, total: str, date: str, delete_order=None, consult_order=None):
        self.id = str(id)
        self.name = name
        self.total = str(total)
        self.date = date
        self.delete_order = delete_order
        self.consult_order = consult_order

class Order(ft.ResponsiveRow):
    def __init__(self, order: OrderInfo, delete_order, consult_order):
        super().__init__()
        self.delete_order = delete_order
        self.consult_order = consult_order
        self.order = order
        self.vertical_alignment = "center"
        self.spacing = 15
        self.controls = [
            ft.Column(
                col=6,
                controls=[
                    ft.Text(value=" Nombre y ID: " + order.name + " #"+order.id, size=20, weight=ft.FontWeight.W_400),
                    ft.Text(value=" Total: " + order.total + "$", size=20),
                    ft.Text(value=" Fecha y Hora: " + order.date, size=20)
                ],
            ),
            ft.Column(
                col=6,
                controls=[
                    ft.Row(
                        controls=[
                            ft.ElevatedButton(
                                content=ft.Container(
                                    content=ft.Row(
                                        [
                                            ft.Text(value="Ver Detalles", size=20),
                                            ft.Icon(name=ft.icons.VISIBILITY, color="blue"),
                                        ],
                                        alignment=ft.MainAxisAlignment.CENTER,
                                        spacing=5,
                                    ),
                                    padding=ft.padding.all(10),
                                    on_click=self.view_clicked,
                                ),
                            ),
                            ft.ElevatedButton(
                                content=ft.Container(
                                    content=ft.Row(
                                        [
                                            ft.Text(value="Eliminar Orden", size=20),
                                            ft.Icon(name=ft.icons.DELETE, color="red"),
                                        ],
                                        alignment=ft.MainAxisAlignment.CENTER,
                                        spacing=5,
                                    ),
                                    padding=ft.padding.all(10),
                                    on_click=self.delete_clicked,
                                ),
                            ),
                        ],
                    ),
                ],
            ),
        ]

    def view_clicked(self, e):
        self.consult_order(self.order, self)
        pass

    def delete_clicked(self, e):
        self.delete_order(self, self.order)
        pass

def print_receipt():
    # You need to replace these with the correct values for your printer
    # Vendor ID and Product ID can be found in your printer's manual or system device manager
    VENDOR_ID = 0x04b8
    PRODUCT_ID = 0x0e28
    try:
        # Initialize USB printer - this will need to be specific to your printer's connection
        printer = Usb(VENDOR_ID, PRODUCT_ID)

        # Ticket Header
        printer.set(bold=True, height=2, width=2)
        printer.text("Puesto BASAÑEZ\n")
        # Reset to normal text after printing the header
        printer.set(bold=False, height=1, width=1)
        printer.text("Cristóbal Colón 401, Zona Centro, 89000 Tampico.\n")
        printer.text("Tel: 833 315 3054\n")
        printer.text("Orden #"+app_state.orderToPrint.id+"\n")
        printer.text(datetime.now().strftime("%Y-%m-%d %H:%M:%S\n"))
        printer.text("--------------------------------\n")

        # Print column headers
        printer.set(align='left', bold=True)
        printer.text("ARTICULO    CANT.           TOTAL\n")
        printer.text("------------------------------------------------\n")
        printer.set(bold=False) 
        
        # Print each item detail
        for item in app_state.detailsToPrint:
            name = item['name'][:12].ljust(12)
            # Assuming quantity is a separate field, or a fixed value if not available
            quantity = "1"  # Replace with actual quantity if available
            unit = item['unit']['name'][:8].rjust(8)
            # Assuming total price needs to be calculated
            total_price = float(quantity) * item['priceUnit']
            total = f"${total_price:.2f}".rjust(12)

            line = f"{name}{quantity} {unit}{total}\n"
            printer.text(line)
        printer.text("------------------------------------------------\n")

        # Add space before the total
        printer.text("\n")

        # Print total in bold with larger font
        printer.set(align='center',bold=True, height=2, width=2)
        printer.text("Total: $" + app_state.orderToPrint.total + "\n")
        # Reset to normal text after printing the total
        printer.set(bold=False, height=1, width=1)
        printer.text("--------------------------------\n")

        printer.text("\n")

        # Footer
        printer.text("¡Gracias por su compra!\n")
        printer.text("¡Regrese pronto!\n")

        # Barcode or QR Code
        printer.qr("https://wa.me/message/JBQLUVO2WXMJJ1")
        #convert the order id to a string EAN8 barcode

        order_id_str = str(app_state.orderToPrint.id)
        # Pad or truncate the order ID to make it 8 digits long
        order_id_str = order_id_str[:8].rjust(8, '0')
        
        # Print the barcode
        printer.barcode(order_id_str, 'EAN8')
        
        # Ensure data is sent before closing
        printer.cut()
        return True, "Receipt printed successfully."
    except Exception as e:
        return False, f"Error printing receipt: {e}"

def get_orders_from_api():
    try:
        response = requests.get("http://localhost:3000/order")
        response.raise_for_status()  # Raises an HTTPError if the HTTP request returned an unsuccessful status code
        orders = response.json()
        # process orders and show only those with status == 'PENDING'
        orders = [order for order in orders if order["status"] == "PENDING"]
        return orders
    except requests.RequestException as e:
        print(f"Error fetching orders: {e}")
        return []

def main(page: ft.Page):
    app_state.previous_pending_count = 0
    page.horizontal_alignment = "stretch"
    page.title = "Manejo de Ordenes"
    page.window_width = 1080       
    page.window_height = 720       
    page.window_resizable = False 
    page.theme_mode = ft.ThemeMode.LIGHT #turn on dark mode

    def format_iso_date(iso_date_str):
        iso_date = iso_date_str.rstrip("Z")
        if "." in iso_date:  # Check if milliseconds are present
            date_format = "%Y-%m-%dT%H:%M:%S.%f"
        else:
            date_format = "%Y-%m-%dT%H:%M:%S"

        # Parse the ISO format date string to a datetime object
        date_object = datetime.strptime(iso_date, date_format)
        
        # Manually format the date using the month mapping
        month = months_in_spanish[date_object.strftime("%B")]
        formatted_date = date_object.strftime(f"%d de {month} de %Y, %I:%M %p")
        
        return formatted_date

    def get_orders(e):
        orders_data = get_orders_from_api()

        for order_data in orders_data:
        
            # Format the date to a more readable format, e.g., "September 1, 2021, 12:00 PM"
            formatted_date = format_iso_date(order_data["date"])

            order = OrderInfo(
                id=order_data["id"],
                name=order_data["name"],
                total=order_data["total"],
                date=formatted_date,  # Format this date as needed
                delete_order=delete_order,  # Replace with actual delete order function
                consult_order=consult_order  # Replace with actual consult order function
            )
            #compare the order with the orderArray to see if it is already in the array
            if not any(order.id == orderInArray.id for orderInArray in app_state.orderArray):
                app_state.orderArray.append(order)
                page.pubsub.send_all(order)
        
        page.update()

    def update_orders(e):
        # Fetch the current list of orders from the API
        orders_data = get_orders_from_api()

        # Create OrderInfo objects
        fetched_orders = []
        for order_data in orders_data:
            order = OrderInfo(
                id=order_data["id"],
                name=order_data["name"],
                total=order_data["total"],
                date=order_data["date"],  # Format this date as needed
                delete_order=delete_order,  # Replace with actual delete order function
                consult_order=consult_order  # Replace with actual consult order function
            )
            fetched_orders.append(order)

        # Identify deleted orders: those that are in app_state.orderArray but not in fetched_orders
        deleted_orders = [order for order in app_state.orderArray if not any(order.id == fetched_order.id for fetched_order in fetched_orders)]

        # Remove deleted orders from orderList
        for order in deleted_orders:
            # Find the corresponding control in orderList
            order_control = next((control for control in orderList.controls if getattr(control, 'order', None) and control.order.id == order.id), None)
            if order_control:
                orderList.controls.remove(order_control)

        # Update app_state.orderArray to reflect the current fetched orders
        app_state.orderArray = fetched_orders

        page.update()

    def query_api_periodically():
        print("Starting API query loop")
        while True:
            if app_state.run_query and app_state.modal_open == False:
                response = requests.get("http://localhost:3000/order")
                if response.status_code == 200:
                    data = response.json()
                    current_pending_count = sum(1 for order in data if order['status'] == 'PENDING')
                    print(f"Current pending count: {current_pending_count}")
                    if current_pending_count > app_state.previous_pending_count:
                        print("New order(s) found!")
                        get_orders(e=None)
                        app_state.previous_pending_count = current_pending_count
                    elif current_pending_count < app_state.previous_pending_count:
                        print("Order(s) deleted!")
                        update_orders(e=None)
                        app_state.previous_pending_count = current_pending_count
                else:
                    print(f"Error fetching orders: {response.status_code}")
                time.sleep(5)

    def on_order(order: OrderInfo):
        orderList.controls.append(Order(order, delete_order, consult_order))
        page.update()

    def delete_order(orderObj: OrderInfo, order: Order ):
        orderList.controls.remove(orderObj)
        app_state.previous_pending_count = app_state.previous_pending_count - 1
        delete_order_details(order.id)
        page.update()

    def close_dlg(e):
        #app_state.currentOrder = OrderInfo("1","Rene", "223.20", "2021-09-01T12:00:00", None, None)
        app_state.modal_open = False 
        app_state.currentId = 0
        app_state.run_query = True
        dlg_modal.open = False
        page.update()
        page.dialog = None

    def close_delete(e):
        orderList.controls.remove(app_state.currentOrder)
        close_dlg(e)
        delete_order_details(app_state.currentId)
        app_state.previous_pending_count = app_state.previous_pending_count - 1

    def delete_order_details(order_id):
        try:
            # Construct the API endpoint URL
            api_url = f'http://localhost:3000/order/{order_id}/details'

            # Send the DELETE request and await the response
            response = requests.delete(api_url)

            if response.status_code == 200:
                print("Order details successfully deleted.")
                # Process successful deletion here
            else:
                print(f"Failed to delete order details. Status code: {response.status_code}")
                # Process failure here
        except Exception as e:
            print(f"An error occurred: {e}")
            # Handle any exceptions such as network errors

    def close_release(e):
        receipt_response = print_receipt()
        if receipt_response == True:
            release_response = release_order(app_state.currentId)
            if release_response == None:
                app_state.currentId = 0
                orderList.controls.remove(app_state.currentOrder)
                app_state.previous_pending_count = app_state.previous_pending_count - 1
            else:
                print(release_response)
                show_banner_click(e)
                #open_error_modal(e)
        else:
            print(receipt_response)
            show_banner_click(e)
            #open_error_modal(e)
        close_dlg(e)

    def release_order(order_id):
        try:
            # Construct the API endpoint URL
            api_url = f'http://localhost:3000/order/{order_id}/release'
            response = requests.post(api_url)

            if response.status_code == 201:
                print("Order successfully released.")
            else:
                print(f"Failed to release order. Status code: {response.status_code}")
        except Exception as e:
            print(f"An error occurred: {e}")     

    orderDetailList = ft.ListView(
        expand=True,
        divider_thickness=2,
        spacing=5,
        auto_scroll=False,
    )
    
    dlg_modal = ft.AlertDialog(
        modal=True,
        title=ft.Text(value="Confirmacion de orden:"),
        content=ft.Column(
            controls=[
                ft.Row(
                    controls=[
                        ft.Text(value="Loading", size=20)
                    ],
                    spacing=10
                )
            ],
            spacing=10
        ),
        actions=[
            ft.ElevatedButton(
                width=270,
                height=50,
                content=ft.Row(
                    [
                        ft.Text(value="Confirmar e Imprimir", size=18),
                        ft.Icon(name=ft.icons.PRINT, color="green"),
                    ],
                    alignment=ft.MainAxisAlignment.SPACE_AROUND,
                ),
                on_click=close_release),
            ft.ElevatedButton(
                width=220,
                height=50,
                content=ft.Row(
                    [
                        ft.Text(value="Eliminar Orden", size=18),
                        ft.Icon(name=ft.icons.DELETE, color="red"),
                    ],
                    alignment=ft.MainAxisAlignment.SPACE_AROUND,
                ),
                on_click=close_delete),
            ft.ElevatedButton(
                width=170,
                height=50,
                content=ft.Row(
                    [
                        ft.Text(value="Regresar", size=18),
                        ft.Icon(name=ft.icons.KEYBOARD_RETURN, color="blue"),
                    ],
                    alignment=ft.MainAxisAlignment.SPACE_AROUND,
                ),
                on_click=close_dlg),
        ],
        actions_alignment=ft.MainAxisAlignment,
        on_dismiss=lambda e: print("Modal dialog dismissed!"),
    )

    def consult_order(order: OrderInfo, orderObj: OrderInfo):
        app_state.currentOrder = orderObj
        app_state.currentId = order.id
        app_state.orderToPrint = order
        print(f"Consulting order: {order.id}")

        response = requests.get(f'http://localhost:3000/order-detail/order/{order.id}')

        if response.status_code == 200:
            items = response.json()
            orderDetailList.controls.clear()  # Clear existing content in orderDetailList
            app_state.detailsToPrint.clear()
            for item in items:
                product = item['product']
                app_state.detailsToPrint.append(product)
                detailItem = ft.Column(
                    controls=[
                        ft.Text(value="Producto: " + product['name'], size=18),
                        ft.Text(value="Cantidad y Unidad: " + str(item['quantity']) + " " + product['unit']['name'], size=18),
                        ft.Text(value="Total: $" + str(item['price']), size=18),
                    ],
                    spacing=5
                )
                orderDetailList.controls.append(detailItem)
        else:
            # Handle errors, such as order not found or server errors
            print("Error fetching order details")
            orderDetailList.controls.clear()  # Clear existing content in case of error
            detailItem = ft.Column(
                controls=[
                    ft.Text(value="Error fetching order details", size=18),
                ],
                spacing=5
            )
            orderDetailList.controls.append(detailItem)

        dlg_modal.content.controls.clear()  # Clear existing content in dlg_modal

        # Create the order header
        orderHeader = [
            ft.Text(value="ID: " + order.name + " #" + order.id, size=20),
            ft.Text(value="Total: " + order.total, size=20),
            ft.Text(value="Fecha y Hora: " + order.date, size=20)
        ]

        # Add the header to dlg_modal first
        dlg_modal.content.controls.extend(orderHeader)

        # Then add the updated orderDetailList
        dlg_modal.content.controls.append(orderDetailList)

        open_dlg_modal(None)

    def open_dlg_modal(e):
        if not app_state.modal_open:
            page.dialog = dlg_modal
            dlg_modal.open = True
            page.update()
            app_state.modal_open = True
            app_state.run_query = False
    
    def close_banner(e):
        page.banner.open = False
        page.update()

    page.banner = ft.Banner(
        bgcolor=ft.colors.AMBER_100,
        leading=ft.Icon(ft.icons.WARNING_AMBER_ROUNDED, color=ft.colors.AMBER, size=40),
        content=ft.Text(
            "Oops, ocurrio un error al imprimir el recibo. Por favor, intente de nuevo.",
        size=20),
        actions=[
            ft.TextButton("Cerrar", icon="close", on_click=close_banner),
        ],
    )

    def show_banner_click(e):
        page.banner.open = True
        page.update()
    
    page.pubsub.subscribe(on_order)

    orderList = ft.ListView(
        expand=True,
        divider_thickness=2,
        spacing=10,
        auto_scroll=False,
    )

    page.add(
        ft.Container(
            content=orderList,
            border=ft.border.all(1, ft.colors.OUTLINE),
            border_radius=5,
            padding=10,
            expand=True,
        ),
        ft.ResponsiveRow(
            [
                ft.ElevatedButton(
                    content=ft.Container(
                        content=ft.Row(
                            [
                                ft.Text(value="Recargar Ordenes", size=20),
                                ft.Icon(name=ft.icons.REFRESH, color="blue"),
                            ],
                            alignment=ft.MainAxisAlignment.CENTER,
                            spacing=5,
                        ),
                        padding=ft.padding.all(10),
                        on_click=get_orders,
                    ),
                ),
            ]
        ),
    )
    query_api_periodically()

if __name__ == "__main__":
   ft.app(target=main)