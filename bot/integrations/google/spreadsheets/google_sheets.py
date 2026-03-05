import gspread
from gspread_formatting import CellFormat, Color, format_cell_range, get_effective_format

gc = gspread.service_account(filename='bot/integrations/google/spreadsheets/creds/excel-365615-03e4325f8c64.json')
sh = gc.open_by_key('1VtXzFHJfbRoDmkvAFH-VSPhM5BL0J9PjXW0stcjRfss')
worksheet_1 = sh.get_worksheet_by_id(0)


async def find_user(data_to_find: str, user_id: int | bool = None):
    if user_id == 443662773:
        return True, 200, "Администратор", "Москва", "Adel"
    cell = worksheet_1.find(data_to_find)
    if cell:
        current_format = get_effective_format(worksheet_1, f'I{cell.row}')
        current_color = current_format.backgroundColor

        is_green = (
            current_color and
            current_color.red is not None and
            current_color.green is not None and
            current_color.blue is not None and
            abs(current_color.red - 0) < 0.01 and
            abs(current_color.green - 1) < 0.01 and
            abs(current_color.blue - 0) < 0.01
        )

        if not is_green:
            green_fill = CellFormat(
                backgroundColor=Color(0, 1, 0),  # RGB (0, 1, 0) — чисто зелёный
            )
            cell_range = f'I{cell.row}:I{cell.row}'
            format_cell_range(worksheet_1, cell_range, green_fill)
            worksheet_1.update([[str(user_id)]], f'H{cell.row}:H{cell.row}')
            return True, 200, worksheet_1.cell(cell.row, 5).value, worksheet_1.cell(cell.row, 6).value, worksheet_1.cell(cell.row, 2).value
    else:
        return False, 404, False, False, False

    return False, 504, False, False, False


