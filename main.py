import pandas as pd
import os
import logging
from flask import Flask, request, jsonify
from src.extract_data import extract_block_data


logging.basicConfig(
    filename='app.log', 
    level=logging.info ,
    format='%(asctime)s [%(levelname)s] %(message)s'
)

app = Flask(__name__)

@app.route('/upload_pdf' , methods=['POST'])  #client HTTP
def upload_invoice():
    try:
        file = request.files.get('file')
        if not file:
            logging.warning('Nenhum arquivo foi reconhecido')
            return jsonify({'error' : 'Nenhum arquivo enviado'}), 400
        
        data = extract_block_data(file)
        logging.info(f"Dados extraídos:{data}")

        output_path = os.path.join('output', 'documentacao_AP.xlsx')
        df = pd.DataFrame([data])
        header = not os.path.exists(output_path)
        df.to_csv(output_path, index=False, mode='a', header=header)

        return jsonify({'message' : 'Dados extraídos e salvos com sucesso', 'dados':data }), 200
    
    except Exception as e:
        logging.exception("erro ao porcessar a invoice")
        return jsonify({'err':'Erro interno no servidor', 'detalhes':str(e) }), 500
    
if __name__ == '__main__':
    app.run(debug=True, port=...)