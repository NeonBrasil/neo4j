import psycopg2
from neo4j import GraphDatabase
import logging
from contextlib import contextmanager

# Configurar logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

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
NEO4J_PASSWORD = ""  # Ajuste conforme necessário

@contextmanager
def get_connections():
    """Context manager para gerenciar conexões com PostgreSQL e Neo4j"""
    pconn = None
    driver = None
    try:
        logger.info("Conectando ao PostgreSQL...")
        pconn = psycopg2.connect(**POSTGRES_CONFIG)
        
        logger.info("Conectando ao Neo4j...")
        driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
        
        yield pconn, driver
        
    except psycopg2.Error as e:
        logger.error(f"Erro PostgreSQL: {e}")
        raise
    except Exception as e:
        logger.error(f"Erro Neo4j: {e}")
        raise
    finally:
        if pconn:
            pconn.close()
            logger.info("Conexão PostgreSQL fechada")
        if driver:
            driver.close()
            logger.info("Conexão Neo4j fechada")

def cria_no(tx, label, props):
    """Cria um nó no Neo4j com validação de dados"""
    # Remove valores None
    clean_props = {k: v for k, v in props.items() if v is not None}
    if clean_props:
        propstr = ', '.join(f"{k}: ${k}" for k in clean_props.keys())
        tx.run(f"MERGE (n:{label} {{ {propstr} }})", **clean_props)

def cria_nos_batch(tx, label, nodes_list):
    """Cria múltiplos nós em batch para melhor performance"""
    if nodes_list:
        # Remove valores None de todos os nós
        clean_nodes = []
        for node in nodes_list:
            clean_node = {k: v for k, v in node.items() if v is not None}
            if clean_node:
                clean_nodes.append(clean_node)
        
        if clean_nodes:
            cypher = f"UNWIND $nodes AS node MERGE (n:{label}) SET n = node"
            tx.run(cypher, nodes=clean_nodes)

def cria_rel(tx, label1, key1, value1, rel, label2, key2, value2, props=None):
    """Cria relacionamento entre dois nós"""
    param_dict = {key1: value1, key2: value2}
    
    if props:
        # Remove valores None das propriedades
        clean_props = {k: v for k, v in props.items() if v is not None}
        if clean_props:
            param_dict.update(clean_props)
            props_str = ', ' + ', '.join(f"{k}: ${k}" for k in clean_props.keys())
        else:
            props_str = ''
    else:
        props_str = ''
    
    cypher = (
        f"MATCH (a:{label1} {{{key1}: ${key1}}}), (b:{label2} {{{key2}: ${key2}}}) "
        f"MERGE (a)-[r:{rel}{{{props_str[2:] if props_str else ''}}}]->(b)"
    )
    tx.run(cypher, **param_dict)

def migrar_dados():
    """Função principal de migração"""
    try:
        with get_connections() as (pconn, driver):
            pcursor = pconn.cursor()
            
            with driver.session() as session:
                # 1. Migrar Departamentos
                logger.info("Migrando departamentos...")
                departments = []
                pcursor.execute("SELECT id, nome FROM departamento")
                for dep in pcursor.fetchall():
                    departments.append({"id": dep[0], "name": dep[1]})
                
                if departments:
                    session.write_transaction(cria_nos_batch, "Department", departments)
                    logger.info(f"Criados {len(departments)} departamentos")

                # 2. Migrar Professores
                logger.info("Migrando professores...")
                professors = []
                pcursor.execute("SELECT id, nome FROM professor")
                for prof in pcursor.fetchall():
                    professors.append({"id": prof[0], "name": prof[1]})
                
                if professors:
                    session.write_transaction(cria_nos_batch, "Professor", professors)
                    logger.info(f"Criados {len(professors)} professores")

                # 3. Relacionamento Chefe de Departamento
                logger.info("Criando relacionamentos chefe-departamento...")
                pcursor.execute("SELECT id, chefe_id FROM departamento WHERE chefe_id IS NOT NULL")
                chefe_count = 0
                for dep_id, chefe_id in pcursor.fetchall():
                    session.write_transaction(
                        cria_rel, "Professor", "id", chefe_id, "HEAD_OF", "Department", "id", dep_id
                    )
                    chefe_count += 1
                logger.info(f"Criados {chefe_count} relacionamentos chefe-departamento")

                # 4. Migrar Cursos
                logger.info("Migrando cursos...")
                courses = []
                course_dept_rels = []
                pcursor.execute("SELECT id, nome, codigo, departamento_id FROM curso")
                for curso in pcursor.fetchall():
                    courses.append({"id": curso[0], "name": curso[1], "code": curso[2]})
                    course_dept_rels.append((curso[0], curso[3]))
                
                if courses:
                    session.write_transaction(cria_nos_batch, "Course", courses)
                    logger.info(f"Criados {len(courses)} cursos")
                    
                    # Relacionamentos curso-departamento
                    for curso_id, dept_id in course_dept_rels:
                        session.write_transaction(
                            cria_rel, "Course", "id", curso_id, "BELONGS_TO", "Department", "id", dept_id
                        )

                # 5. Migrar Currículos
                logger.info("Migrando currículos...")
                curricula = []
                curriculum_course_rels = []
                pcursor.execute("SELECT id, curso_id, ano, versao FROM curriculo")
                for curr in pcursor.fetchall():
                    curricula.append({"id": curr[0], "year": curr[2], "version": curr[3]})
                    curriculum_course_rels.append((curr[1], curr[0]))
                
                if curricula:
                    session.write_transaction(cria_nos_batch, "Curriculum", curricula)
                    logger.info(f"Criados {len(curricula)} currículos")
                    
                    # Relacionamentos curso-currículo
                    for curso_id, curr_id in curriculum_course_rels:
                        session.write_transaction(
                            cria_rel, "Course", "id", curso_id, "HAS_CURRICULUM", "Curriculum", "id", curr_id
                        )

                # 6. Migrar Disciplinas
                logger.info("Migrando disciplinas...")
                subjects = []
                subject_dept_rels = []
                pcursor.execute("SELECT id, nome, codigo, departamento_id FROM disciplina")
                for disc in pcursor.fetchall():
                    subjects.append({"id": disc[0], "name": disc[1], "code": disc[2]})
                    subject_dept_rels.append((disc[0], disc[3]))
                
                if subjects:
                    session.write_transaction(cria_nos_batch, "Subject", subjects)
                    logger.info(f"Criadas {len(subjects)} disciplinas")
                    
                    # Relacionamentos disciplina-departamento
                    for subj_id, dept_id in subject_dept_rels:
                        session.write_transaction(
                            cria_rel, "Subject", "id", subj_id, "BELONGS_TO", "Department", "id", dept_id
                        )

                # 7. Relacionamentos Currículo-Disciplina
                logger.info("Criando relacionamentos currículo-disciplina...")
                pcursor.execute("SELECT curriculo_id, disciplina_id FROM curriculo_disciplina")
                curr_disc_count = 0
                for curr_id, disc_id in pcursor.fetchall():
                    session.write_transaction(
                        cria_rel, "Curriculum", "id", curr_id, "INCLUDES", "Subject", "id", disc_id
                    )
                    curr_disc_count += 1
                logger.info(f"Criados {curr_disc_count} relacionamentos currículo-disciplina")

                # 8. Migrar Alunos
                logger.info("Migrando alunos...")
                students = []
                student_course_rels = []
                pcursor.execute("SELECT id, nome, curso_id FROM aluno")
                for al in pcursor.fetchall():
                    students.append({"id": al[0], "name": al[1]})
                    student_course_rels.append((al[0], al[2]))
                
                if students:
                    session.write_transaction(cria_nos_batch, "Student", students)
                    logger.info(f"Criados {len(students)} alunos")
                    
                    # Relacionamentos aluno-curso
                    for student_id, course_id in student_course_rels:
                        session.write_transaction(
                            cria_rel, "Student", "id", student_id, "ENROLLED_IN", "Course", "id", course_id
                        )

                # 9. Relacionamentos Aluno-Disciplina (Histórico)
                logger.info("Criando relacionamentos aluno-disciplina...")
                pcursor.execute("SELECT aluno_id, disciplina_id, ano, semestre, nota FROM aluno_disciplina")
                student_subj_count = 0
                for row in pcursor.fetchall():
                    props = {"year": row[2], "semester": row[3], "final_grade": row[4]}
                    session.write_transaction(
                        cria_rel, "Student", "id", row[0], "TOOK", "Subject", "id", row[1], props
                    )
                    student_subj_count += 1
                logger.info(f"Criados {student_subj_count} relacionamentos aluno-disciplina")

                # 10. Relacionamentos Professor-Disciplina
                logger.info("Criando relacionamentos professor-disciplina...")
                pcursor.execute("SELECT professor_id, disciplina_id, ano, semestre FROM professor_disciplina")
                prof_subj_count = 0
                for row in pcursor.fetchall():
                    props = {"year": row[2], "semester": row[3]}
                    session.write_transaction(
                        cria_rel, "Subject", "id", row[1], "TAUGHT_BY", "Professor", "id", row[0], props
                    )
                    prof_subj_count += 1
                logger.info(f"Criados {prof_subj_count} relacionamentos professor-disciplina")

                # 11. Migrar Grupos TCC
                logger.info("Migrando grupos TCC...")
                tcc_groups = []
                tcc_advisor_rels = []
                pcursor.execute("SELECT id, titulo, ano, semestre, professor_orientador_id FROM tcc_grupo")
                for row in pcursor.fetchall():
                    gid, titulo, ano, semestre, orientador_id = row
                    tcc_groups.append({"id": gid, "title": titulo, "year": ano, "semester": semestre})
                    if orientador_id:
                        tcc_advisor_rels.append((gid, orientador_id))
                
                if tcc_groups:
                    session.write_transaction(cria_nos_batch, "TCCGroup", tcc_groups)
                    logger.info(f"Criados {len(tcc_groups)} grupos TCC")
                    
                    # Relacionamentos TCC-Orientador
                    for group_id, advisor_id in tcc_advisor_rels:
                        session.write_transaction(
                            cria_rel, "TCCGroup", "id", group_id, "ADVISED_BY", "Professor", "id", advisor_id
                        )

                # 12. Relacionamentos Aluno-TCC
                logger.info("Criando relacionamentos aluno-TCC...")
                pcursor.execute("SELECT grupo_id, aluno_id FROM tcc_aluno")
                tcc_student_count = 0
                for row in pcursor.fetchall():
                    session.write_transaction(
                        cria_rel, "Student", "id", row[1], "MEMBER_OF", "TCCGroup", "id", row[0]
                    )
                    tcc_student_count += 1
                logger.info(f"Criados {tcc_student_count} relacionamentos aluno-TCC")

        logger.info("✅ Migração concluída com sucesso!")
        
    except Exception as e:
        logger.error(f"❌ Erro durante a migração: {e}")
        raise

if __name__ == "__main__":
    migrar_dados()
