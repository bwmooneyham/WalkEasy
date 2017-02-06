from flask import render_template
from flask import request
from Routing import Routing_func
from WalkEasy import app
from sqlalchemy import create_engine
from sqlalchemy_utils import database_exists, create_database
import pandas as pd
import psycopg2

@app.route('/')
@app.route('/input')
def cesareans_input():
    return render_template("input_valid.html")

@app.route('/output')
def cesareans_output():
    #Get user-specified start/end locations
    start_address = request.args.get('start_address')
    end_address = request.args.get('end_address')
    
    #Provide defaults in case of no user input
    if len(start_address) < 2:
        start_address = "Fisherman's Wharf, San Francisco"
    if len(end_address) < 2:
        end_address = "Golden Gate Park, San Francisco"
    
    #Get user-specified slider value
    easy_hard_preference = request.args.get('easy_hard_preference')
    easy_hard_preference = int(easy_hard_preference)

    #Run routing given user-specified inputs
    the_result, User_Total_Dist_mi, Percent_Longer, Percent_Harder, User_Total_Cal, lat1, long1, lat2, long2, Dist_Longer, Cals_Saved, Dist_Shorter, Cals_Extra = Routing_func(start_address,end_address,easy_hard_preference)

    #Send back to input page if locations provided by user are not in SF area
    if long1 < 37.7 or long1 > 37.81 or long2 < 37.7 or long2 > 37.81 or lat1 < -122.52 or lat1 > -122.35 or lat2 < -122.52 or lat2 > -122.35:
        return render_template("input_invalid.html")

    #Customize output metrics depending on slider value
    if easy_hard_preference > 95:
        return render_template("output_easiest.html", the_result = the_result, User_Total_Dist_mi = User_Total_Dist_mi, Percent_Longer = Percent_Longer, Percent_Harder = Percent_Harder, User_Total_Cal = User_Total_Cal, lat1 = lat1, long1 = long1, lat2 = lat2, long2 = long2 , Dist_Longer = Dist_Longer, Cals_Saved = Cals_Saved, Dist_Shorter = Dist_Shorter, Cals_Extra = Cals_Extra)
    elif easy_hard_preference < 5:
        return render_template("output_shortest.html", the_result = the_result, User_Total_Dist_mi = User_Total_Dist_mi, Percent_Longer = Percent_Longer, Percent_Harder = Percent_Harder, User_Total_Cal = User_Total_Cal, lat1 = lat1, long1 = long1, lat2 = lat2, long2 = long2 , Dist_Longer = Dist_Longer, Cals_Saved = Cals_Saved, Dist_Shorter = Dist_Shorter, Cals_Extra = Cals_Extra)
    else:
        return render_template("output_middle.html", the_result = the_result, User_Total_Dist_mi = User_Total_Dist_mi, Percent_Longer = Percent_Longer, Percent_Harder = Percent_Harder, User_Total_Cal = User_Total_Cal, lat1 = lat1, long1 = long1, lat2 = lat2, long2 = long2 , Dist_Longer = Dist_Longer, Cals_Saved = Cals_Saved, Dist_Shorter = Dist_Shorter, Cals_Extra = Cals_Extra)
