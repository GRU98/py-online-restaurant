from app import app, start_discount_sender, start_birthday_checker
from app.seed import ensure_admin_exists, seed_initial_menu, seed_restaurant_tables

if __name__ == "__main__":
    ensure_admin_exists()
    seed_initial_menu()
    seed_restaurant_tables()
    start_discount_sender()
    start_birthday_checker()
    app.run(debug=True)
