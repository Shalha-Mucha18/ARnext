from sqlalchemy import text

def get_uom_conversion_sql() -> str:
    """
    Returns the centralized SQL CASE statement for UOM conversion.
    Only specific units (4, 144, 188, 189, 232) are converted to MT.
    All other units use their base UOM without conversion.
    """
    return """
        CASE
            WHEN unit_id = 4 AND base_uom = 'Ton' THEN delivery_qty
            WHEN unit_id = 4 THEN (delivery_qty * numgrossweight) / 1000.0
            WHEN unit_id IN (188, 189, 232) THEN (delivery_qty * numgrossweight) / 1000.0
            WHEN unit_id = 144 AND base_uom = 'Metric Tons' THEN delivery_qty
            WHEN unit_id = 144 THEN (delivery_qty * numgrossweight) / 1000.0
            ELSE delivery_qty
        END
    """

def get_uom_display() -> str:
    """
    Returns SQL to determine the display UOM.
    Specific units show 'MT', others show their base_uom.
    """
    return """
        CASE
            WHEN unit_id IN (4, 144, 188, 189, 232) THEN 'MT'
            ELSE COALESCE(base_uom, 'Units')
        END
    """
