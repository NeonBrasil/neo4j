# neo4j

### O banco foi estruturado com os seguintes labels de nós e relacionamentos:

## Labels de Nós

**Student**: Alunos(as) (nome, id)

**Professor**: Professores(as) (nome, id)

**Course**: Cursos (nome, código)

**Department**: Departamentos acadêmicos (nome)

**Subject**: Disciplinas (nome, código)

**Curriculum**: Matrizes curriculares (ano, versão)

**TCCGroup**: Grupos de Trabalho de Conclusão de Curso (título, ano, semestre)

**Tipos de Relacionamento**

**ENROLLED_IN**: Aluno matriculado em um curso

**HAS_CURRICULUM**: Curso possui matriz curricular

**INCLUDES**: Matrícula curricular inclui disciplina

**BELONGS_TO**: Curso ou disciplina pertencente a departamento

**HEAD_OF**: Professor chefe de departamento

**TOOK**: Aluno cursou disciplina (ano, semestre, nota final)

**TAUGHT_BY**: Professor ministrou disciplina (ano, semestre)

**MEMBER_OF**: Aluno membro de grupo de TCC

**ADVISED_BY**: Professor orientador de grupo de TCC

## Como Executar o Projeto
- Neo4j Desktop ou acesso ao Neo4j Browser
**Passo a Passo**
- Copie e cole os comandos de criação do modelo no Neo4j Browser presentes nos arquivos "CriacaoDeNos" e "relacionamentos" no Main

![image](https://github.com/user-attachments/assets/493398e4-3aad-4ee5-8280-7e880d88f72f)

