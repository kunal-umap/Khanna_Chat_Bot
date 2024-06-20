from fastapi import FastAPI
from fastapi import Request
from fastapi.responses import JSONResponse
import db_functions
import general_function

app = FastAPI()
inprogress_orders = {}

@app.post("/")
async def handle_request(request: Request):
    payload = await request.json()

    intent = payload["queryResult"]["intent"]["displayName"]
    parametes = payload["queryResult"]["parameters"]
    output_content = payload["queryResult"]["outputContexts"]
    session_id = general_function.extract_session(output_content[0]["name"])

    intent_handle = {
        "track.order - context: ongoing-order": track_order,
        "order.add - context: ongoing-order": add_order,
        "order.complete - context: ongoing-order": complete_order,
        "order.remove - context: ongoing-order": remove_order
    }

    return intent_handle[intent](parametes,session_id)



def save_to_db(order: dict):
    next_order_id = db_functions.get_next_order_id()

    for food_item, quantity in order.items():
        rcode = db_functions.insert_order_item(
            food_item,
            quantity,
            next_order_id
        )

        if rcode == -1:
            return -1

    db_functions.insert_order_tracking(next_order_id, "in progress")

    return next_order_id



def remove_order(parameter: dict, session_id: str):
    if session_id not in inprogress_orders:
        return JSONResponse(content={
            "fulfillmentText": "I'm having a trouble finding your order. Sorry! Can you place a new order please?"
        })
    food_items = parameter["food-item"]
    current_order = inprogress_orders[session_id]

    removed_items = []
    no_such_items = []

    for item in food_items:
        if item not in current_order:
            no_such_items.append(item)
        else:
            removed_items.append(item)
            del current_order[item]
    if len(removed_items) > 0:
        fulfillment_text = f'Removed {",".join(removed_items)} from your order!'
    if len(no_such_items) > 0:
        fulfillment_text = f' Your current order does not have {",".join(no_such_items)}'
    if len(current_order.keys()) == 0:
        fulfillment_text += " Your order is empty!"
    else:
        order_str = general_function.get_str_from_food_dict(current_order)
        fulfillment_text += f" Here is what is left in your order: {order_str}"

    return JSONResponse(content={
        "fulfillmentText": fulfillment_text
    })


def complete_order(parameter: dict, session_id: str):
    if session_id not in inprogress_orders:
        fulfillment_text = "I'm having a trouble finding your order. Sorry! Can you place a new order please?"
    else:
        order = inprogress_orders[session_id]
        order_id = save_to_db(order)
        if order_id == -1:
            fulfillment_text = "Sorry, I couldn't process your order due to a backend error. " \
                               "Please place a new order again"
        else:
            order_total = db_functions.get_total_order_price(order_id)

            fulfillment_text = f"Awesome. We have placed your order. " \
                               f"Here is your order id # {order_id}. " \
                               f"Your order total is {order_total} which you can pay at the time of delivery!"

        del inprogress_orders[session_id]

    return JSONResponse(content={
        "fulfillmentText": fulfillment_text
    })


def add_order(parameter: dict, session_id: str):
    food_items = parameter["food-item"]
    quantities = parameter["number"]
    if len(food_items) != len(quantities):
        fulfil_text = "Sorry I didn't , please specify quantity clearly"
    else:
        new_dict = dict(zip(food_items, quantities))
        if session_id in inprogress_orders:
            current_dict = inprogress_orders[session_id]
            current_dict.update(new_dict)
            inprogress_orders[session_id] = current_dict
        else:
            inprogress_orders[session_id] = new_dict

        order_str = general_function.get_str_from_food_dict(inprogress_orders[session_id])
        fulfil_text = f"so the order are: {order_str}. Do you want to add anything else?"

    return  JSONResponse(content={
        "fulfillmentText": fulfil_text
    })





def track_order(parameters: dict,s:str):
    order_id = int(parameters["order_id"])
    order_status = db_functions.get_order_status(order_id)
    if order_status:
        fulFil_text = f"The order status for order id: {order_id} is: {order_status}"
    else:
        fulFil_text = f"The order with order id: {order_id} Not Found"

    print(fulFil_text)

    return JSONResponse(content={
        "fulfillmentText": fulFil_text
    })