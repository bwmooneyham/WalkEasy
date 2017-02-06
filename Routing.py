def Routing_func(start_address,end_address,easy_hard_preference):

    from sqlalchemy import create_engine
    import psycopg2
    import pandas as pd
    import numpy as np

    ## CONNECT TO SQL DATABASE:

    # Provide database info
    dbname = '' #ENTER DATABASE NAME HERE
    pswd = 'abc123' #ENTER PASSWORD HERE
    username = 'postgres' #ENTER POSTGRES USERNAME HERE

    # construct a connection to a database
    engine = create_engine('postgresql://%s:%s@localhost/%s'%(username,pswd,dbname))

    # connect to the database
    con = None
    con = psycopg2.connect(database = dbname, user = username, host='localhost', password=pswd)
    
    from mapbox import Geocoder

    MAPBOX_ACCESS_TOKEN="" #ENTER MAPBOX API TOKEN HERE
    
    geocoder = Geocoder(access_token=MAPBOX_ACCESS_TOKEN)

    #Get coordinates for Route starting location
    response_start = geocoder.forward(start_address)
    start_coords = response_start.geojson()['features'][0]['geometry']['coordinates']
    lat1 = start_coords[0]
    long1 = start_coords[1]

    #Get coordinates for Route ending location
    response_end = geocoder.forward(end_address)
    end_coords = response_end.geojson()['features'][0]['geometry']['coordinates']
    lat2 = end_coords[0]
    long2 = end_coords[1]

    #Translte coordinates into vertex ids within Postgres tables
    cur_get_ids_from_ll_start = con.cursor()
    cur_get_ids_from_ll_end = con.cursor()
    cur_get_ids_from_ll_start.execute("""select id from ways_vertices_pgr order by st_distance(the_geom, st_setsrid(st_makepoint(%s, %s), 4326)) limit 1;""", (lat1, long1))
    cur_get_ids_from_ll_end.execute("""select id from ways_vertices_pgr order by st_distance(the_geom, st_setsrid(st_makepoint(%s, %s), 4326)) limit 1;""", (lat2, long2))

    id_start = cur_get_ids_from_ll_start.fetchall()
    id_end = cur_get_ids_from_ll_end.fetchall()

    #Calculate Easiest Path
    curX = con.cursor()
    curX.execute("""SELECT id, lon, lat, route.cost, route.edge, new_ways.length_ft
        FROM ways_vertices_pgr
        JOIN
        (SELECT * FROM pgr_dijkstra('
        SELECT gid AS id,
        source,
        target,
        cal_cost AS cost
        FROM ways_act_cals WHERE class_id < 101 OR class_id > 101',
        %s, %s, directed := false )) AS route
        ON
        ways_vertices_pgr.id = route.node
        JOIN (SELECT gid, length_ft FROM ways_act_cals) AS new_ways
        ON new_ways.gid = route.edge
        ORDER BY seq;""", (id_start, id_end))
    Easy_Path = curX.fetchall()

    #Easiest Path Metrics
    Easy_Total_Cal = 0
    Easy_Total_Dist = 0
    for i in range(len(Easy_Path)):
        Easy_Total_Cal += Easy_Path[i][3]
        Easy_Total_Dist += Easy_Path[i][5]

    #Calculate Shortest Path
    curY = con.cursor()
    curY.execute("""SELECT id, lon, lat, route.cost, route.edge, new_ways.cal_cost
        FROM ways_vertices_pgr
        JOIN
        (SELECT * FROM pgr_dijkstra('
        SELECT gid AS id,
        source,
        target,
        length_ft AS cost
        FROM ways_act_cals WHERE class_id < 101 OR class_id > 101',
        %s, %s, directed := false )) AS route
        ON
        ways_vertices_pgr.id = route.node
        JOIN (SELECT gid, cal_cost FROM ways_act_cals) AS new_ways
        ON new_ways.gid = route.edge
        ORDER BY seq;""", (id_start, id_end))
    Short_Path = curY.fetchall()

    #Shortest Path Metrics
    Short_Total_Cal = 0
    Short_Total_Dist = 0
    for i in range(len(Short_Path)):
        Short_Total_Dist += Short_Path[i][3]
        Short_Total_Cal += Short_Path[i][5]

    #Convert slider info into a proportion value (between 0 and 1)
    easy_hard_preference = int(easy_hard_preference)
    easy_hard_preference = easy_hard_preference/100

    #Use slider info to calculate User-specified Route
    curZ = con.cursor()
    curZ.execute("""SELECT id, lon, lat, route.cost, route.edge, new_ways.length_ft, new_ways.cal_cost
        FROM ways_vertices_pgr
        JOIN
        (SELECT * FROM pgr_dijkstra('
        SELECT gid AS id,
        source,
        target,
        ((%s)*cal_cost + (1 - %s)*length_ft) AS cost
        FROM ways_act_cals WHERE class_id < 101 OR class_id > 101',
        %s, %s, directed := false )) AS route
        ON
        ways_vertices_pgr.id = route.node
        JOIN (SELECT gid, length_ft, cal_cost FROM ways_act_cals) AS new_ways
        ON new_ways.gid = route.edge
        ORDER BY seq;""", (easy_hard_preference, easy_hard_preference, id_start, id_end))
    User_Path = curZ.fetchall()

    #User-specified Route Metrics
    User_Total_Cal = 0
    User_Total_Dist = 0
    for i in range(len(User_Path)):
        User_Total_Cal += User_Path[i][6]
        User_Total_Dist += User_Path[i][5]
 
 
    #Write User-Specified Path (concatenate many individual line segments)
    Route_Coords = []
    
    for i in range(len(User_Path)):
        Route_Coords.append([float(User_Path[i][1]),float(User_Path[i][2])])
    
    for i in range(len(Route_Coords)):
        Route_Coords[i][0], Route_Coords[i][1] = Route_Coords[i][1], Route_Coords[i][0]

    Route_str = "["
    for i in range(len(Route_Coords)):
        Route_str += "["
        Route_str += str(Route_Coords[i][0])
        Route_str += ","
        Route_str += str(Route_Coords[i][1])
        Route_str += "]"
        Route_str += ","
    Route_str = Route_str[:-1]
    Route_str += "];"

    the_result = Route_str

    #Final Metrics to Output
    User_Total_Dist_mi = User_Total_Dist/5280
    User_Total_Dist_mi = round(User_Total_Dist_mi,3)
    User_Total_Cal_act = round(User_Total_Cal*80.7*0.0003,3)
    Percent_Longer = ((User_Total_Dist/Short_Total_Dist)-1)*100
    Percent_Longer = round(Percent_Longer,3)
    Percent_Harder = ((User_Total_Cal/Easy_Total_Cal)-1)*100
    Percent_Harder = round(Percent_Harder,3)

    Dist_Longer = User_Total_Dist_mi - (Short_Total_Dist/5280)
    Cals_Saved = round(Short_Total_Cal*80.7*0.0003,3) - User_Total_Cal_act
    Dist_Shorter = (Easy_Total_Dist/5280) - User_Total_Dist_mi
    Cals_Extra = User_Total_Cal_act - round(Easy_Total_Cal*80.7*0.0003,3)
    
    Dist_Longer = round(Dist_Longer,3)
    Cals_Saved = round(Cals_Saved,3)
    Dist_Shorter = round(Dist_Shorter,3)
    Cals_Extra = round(Cals_Extra,3)
    

    return the_result, User_Total_Dist_mi, Percent_Longer, Percent_Harder, User_Total_Cal_act, lat1, long1, lat2, long2, Dist_Longer, Cals_Saved, Dist_Shorter, Cals_Extra
