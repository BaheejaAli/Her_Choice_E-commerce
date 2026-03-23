# Her Choice – E-Commerce Website 🛍️

Her Choice is a production-ready e-commerce platform built with **Django** and **PostgreSQL**, designed for scalability, security, and real-world deployment.

It goes beyond basic CRUD by implementing advanced features like a referral reward system, OTP-based authentication, wallet management, and DevOps-based deployment architecture.


## 🌟 Advanced Features
🔐 Custom Authentication & Security
- Custom User Model extending Django’s AbstractBaseUser (Email/Phone login)
- Email OTP verification for secure registration & password reset
- Secure session handling and environment-based configuration using django-environ

💰 Growth & Engagement Tools
- Referral Engine: Unique alphanumeric referral system rewarding both users
- Wallet System: Virtual wallet for referral rewards and promotional credits

📦 Inventory & UX
- Multi-image upload with cropping support for consistent UI
- Soft-delete mechanism for maintaining historical order data

🛒 Core E-Commerce Features
- Product listing with category & brand filtering
- Add to cart and dynamic quantity management
- Order placement and checkout flow
- Order summary with tax calculation
- Coupon and discount support
- Wishlist functionality

## 🛠️ Tech Stack
| **Layer**        | **Technology**             | **Purpose & Implementation**                                          |
| ---------------- | -------------------------- | --------------------------------------------------------------------- |
| Backend          | Python 3.10+ / Django      | Core business logic, ORM, and secure middleware.                      |
| Database         | PostgreSQL                 | Relational data management with complex query optimization.           |
| Frontend         | HTML5 / CSS3 / JS          | Semantic structure, custom styling, and dynamic DOM manipulation.     |
| DevOps           | AWS EC2 / Nginx / Gunicorn | Production-grade hosting with reverse proxy and WSGI management.      |
| Version Control  | Git / GitHub               | GitFlow-based workflow (Main, Develop, Feature branches)          |


##  📸 Screenshots
🏠 Home Page
🛍️ Product Listing & Filters
🛒 Shopping Cart


## 📂 Architecture & Workflow
The project is structured to remain modular and scalable as the application grows. Each feature (Accounts, Products, Referrals) is isolated into its own Django app.
```
Her-Choice/
├── core/                      # Project configuration (settings, urls, wsgi, asgi)
│
├── apps/
│   ├── accounts/              # Custom user model, authentication, OTP logic
│   ├── adminpanel/            # Admin dashboard & management features
│   ├── brandsandcategories/   # Brand & category management
│   ├── products/              # Product listing, details, inventory
│   ├── cart/                  # Cart functionality
│   ├── orders/                # Order processing & checkout
│   ├── offer/                 # Offers & discounts logic
│   ├── wallet/                # Wallet, transactions, payments
│   └── user_section/          # User profile, dashboard, settings
│
├── static/                    # Global static files (CSS, JS, images)
├── templates/                 # Shared & reusable templates
│
├── .github/workflows/         # CI/CD pipelines (GitHub Actions)
├── .env                       # Environment variables
├── requirements.txt           # Python dependencies
├── manage.py                  # Django management script
└── README.md                  # Project documentation
```

## 🚀 Deployment & DevOps

This project is optimized for production environments:

- Nginx → Reverse proxy, static files, SSL termination
- Gunicorn → WSGI application server
- AWS EC2 → Cloud hosting
- Automated:
  - Static file collection
  - Database migrations

## ⚙️ Setup Instructions

```bash
  # Clone the repository
  git clone https://github.com/BaheejaAli/Her_Choice_E-commerce.git
  
  # Navigate to project
  cd her_choice
  
  # Create virtual environment
  python -m venv venv
  
  # Activate virtual environment
  source venv/bin/activate   # Linux/Mac
  venv\Scripts\activate      # Windows
  
  # Install dependencies
  pip install -r requirements.txt
  
  # Apply migrations
  python manage.py migrate
  
  # Run server
  python manage.py runserver
```
## 🎯 Key Highlights
- Scalable Django architecture
- Secure authentication system
- Real-world e-commerce workflow
- Production deployment with DevOps tools
- Clean UI with custom styling




