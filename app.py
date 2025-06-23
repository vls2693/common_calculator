from common_calc.base import receiver
from flask import Flask, render_template, request
app = Flask(__name__)
app.config['TEMPLATES_AUTO_RELOAD'] = True


@app.route("/")
def index():
    return render_template('index.html')


@app.route('/', methods=['POST'])
def my_form_post():
    whole_dict = request.form
    names, amount, average, debt, overpay, transactions = receiver(whole_dict)
    return render_template('result.html', name_list=names, common_spent_sum=amount, average_sum=average, debt_list=debt,
                           overpay_list=overpay, transaction_list=transactions)


if __name__ == "__main__":
    app.run()
