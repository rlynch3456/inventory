from flask import redirect, render_template
import datetime
from PIL import Image
from pathlib import Path

def create_thumbnail(image_path, output_path, height=100, width=100):
    
    # make new filename from input path
    path = Path(image_path)
    output_file = output_path + path.stem + "_thumb" + path.suffix

    image = Image.open(image_path)
    # if the original image is bigger than the requested size, create the thumbnal
    if image.size[0] > width:
        image.thumbnail((height, width))
        image.save(output_file)
        return path.stem + "_thumb" + path.suffix
    else:
        return "None"



def get_date_string():
    """Format current date string"""
    today = datetime.datetime.now()

    return f"{today.strftime('%Y-%m-%d')}"

def get_date_time_string():
    now = datetime.datetime.now()

    return f"{now.strftime('%Y%m%d%H%M%S')}"
    
def usd(value):
    """Format value as USD."""
    return f"${value:,.2f}"    

def apology(message, code=400):
    print(f"apology message: {message}")
    """Render message as an apology to user."""
    def escape(s):
        """
        Escape special characters.

        https://github.com/jacebrowning/memegen#special-characters
        """
        for old, new in [("-", "--"), (" ", "-"), ("_", "__"), ("?", "~q"),
                         ("%", "~p"), ("#", "~h"), ("/", "~s"), ("\"", "''")]:
            s = s.replace(old, new)
        return s
    return render_template("apology.html", top=code, bottom=escape(message)), code