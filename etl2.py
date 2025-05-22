import psycopg2
from neo4j import GraphDatabase

# Configurações do banco
POSTGRES_CONFIG = {
    'dbname': 'Faculdade',
    'user': 'neon',
    'password': '1234',
    'host': 'localhost',
    'port': 5432
}

NEO4J_URI = "bolt://localhost:7687"
NEO4J_USER = "neo4j"
NEO4J_PASSWORD = "" #nesse caso preferi n colocar a senha aqkkkk

pconn = psycopg2.connect(**POSTGRES_CONFIG)
pcursor = pconn.cursor()

driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))

def cria_no(tx, label, props):
    propstr = ', '.join(f"{k}: ${k}" for k in props.keys())
    tx.run(f"MERGE (n:{label} {{ {propstr} }})", **props)

def cria_rel(tx, label1, key1, value1, rel, label2, key2, value2, props=None):
    props_cypher = (', ' + ', '.join(f"{k}: ${k}" for k in (props or {}).keys())) if props else ''
    param_dict = {f"{key1}": value1, f"{key2}": value2}
    if props:
        param_dict.update(props)
    cypher = (
        f"MATCH (a:{label1} {{{key1}: ${key1}}}), (b:{label2} {{{key2}: ${key2}}}) "
        f"MERGE (a)-[r:{rel}{{{props_cypher[2:]}}}]->(b)"
    )
    tx.run(cypher, **param_dict)

with driver.session() as session:

    pcursor.execute("SELECT id, nome FROM departamento")
    for dep in pcursor.fetchall():
        session.write_transaction(cria_no, "Department", {"id": dep[0], "name": dep[1]})

    pcursor.execute("SELECT id, nome FROM professor")
    for prof in pcursor.fetchall():
        session.write_transaction(cria_no, "Professor", {"id": prof[0], "name": prof[1]})

    pcursor.execute("SELECT id, chefe_id FROM departamento WHERE chefe_id IS NOT NULL")
    for dep_id, chefe_id in pcursor.fetchall():
        session.write_transaction(
            cria_rel, "Professor", "id", chefe_id, "HEAD_OF", "Department", "id", dep_id, None
        )

    pcursor.execute("SELECT id, nome, codigo, departamento_id FROM curso")
    for curso in pcursor.fetchall():
        props = {"id": curso[0], "name": curso[1], "code": curso[2]}
        session.write_transaction(cria_no, "Course", props)
        session.write_transaction(
            cria_rel, "Course", "id", curso[0], "BELONGS_TO", "Department", "id", curso[3]
        )

    pcursor.execute("SELECT id, curso_id, ano, versao FROM curriculo")
    for curr in pcursor.fetchall():
        props = {"id": curr[0], "year": curr[2], "version": curr[3]}
        session.write_transaction(cria_no, "Curriculum", props)
        session.write_transaction(
            cria_rel, "Course", "id", curr[1], "HAS_CURRICULUM", "Curriculum", "id", curr[0]
        )

    pcursor.execute("SELECT id, nome, codigo, departamento_id FROM disciplina")
    for disc in pcursor.fetchall():
        props = {"id": disc[0], "name": disc[1], "code": disc[2]}
        session.write_transaction(cria_no, "Subject", props)
        session.write_transaction(
            cria_rel, "Subject", "id", disc[0], "BELONGS_TO", "Department", "id", disc[3]
        )

    pcursor.execute("SELECT curriculo_id, disciplina_id FROM curriculo_disciplina")
    for curr_id, disc_id in pcursor.fetchall():
        session.write_transaction(
            cria_rel, "Curriculum", "id", curr_id, "INCLUDES", "Subject", "id", disc_id
        )

    pcursor.execute("SELECT id, nome, curso_id FROM aluno")
    for al in pcursor.fetchall():
        props = {"id": al[0], "name": al[1]}
        session.write_transaction(cria_no, "Student", props)
        session.write_transaction(
            cria_rel, "Student", "id", al[0], "ENROLLED_IN", "Course", "id", al[2]
        )

    pcursor.execute("SELECT aluno_id, disciplina_id, ano, semestre, nota FROM aluno_disciplina")
    for row in pcursor.fetchall():
        props = {"year": row[2], "semester": row[3], "final_grade": row[4]}
        session.write_transaction(
            cria_rel, "Student", "id", row[0], "TOOK", "Subject", "id", row[1], props
        )

    pcursor.execute("SELECT professor_id, disciplina_id, ano, semestre FROM professor_disciplina")
    for row in pcursor.fetchall():
        props = {"year": row[2], "semester": row[3]}
        session.write_transaction(
            cria_rel, "Subject", "id", row[1], "TAUGHT_BY", "Professor", "id", row[0], props
        )

    pcursor.execute("SELECT id, titulo, ano, semestre, professor_orientador_id FROM tcc_grupo")
    for row in pcursor.fetchall():
        gid, titulo, ano, semestre, orientador_id = row
        props = {"id": gid, "title": titulo, "year": ano, "semester": semestre}
        session.write_transaction(cria_no, "TCCGroup", props)
        if orientador_id:
            session.write_transaction(
                cria_rel, "TCCGroup", "id", gid, "ADVISED_BY", "Professor", "id", orientador_id
            )

    pcursor.execute("SELECT grupo_id, aluno_id FROM tcc_aluno")
    for row in pcursor.fetchall():
        session.write_transaction(
            cria_rel, "Student", "id", row[1], "MEMBER_OF", "TCCGroup", "id", row[0]
        )

print('Migração concluída!')
pcursor.close()
pconn.close()
driver.close()
