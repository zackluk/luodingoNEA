from app import createApp

app = createApp()

if __name__ == '__main__':
    app.run(port = 5000, debug = True)
    #setting debug to True for now