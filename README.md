# Révisions

Quiz de révision en maths et en physique-chimie, avec la correction expliquée après chaque question.

Le site est statique : il n'y a rien à compiler. GitHub Pages sert directement les fichiers de la branche `main`.

## Organisation

```
index.html                 page unique du site
assets/app.js              affichage des matières, des thèmes et des quiz
assets/style.css           mise en forme
quiz/catalogue.json        liste des matières et des thèmes
quiz/<matière>/<thème>.json   les questions d'un quiz
```

Les adresses du site suivent la même logique :

- `#/` : choix de la matière
- `#/physique-chimie` : choix du thème
- `#/physique-chimie/dosages-spectres-ir` : le quiz (ce lien peut être partagé tel quel)

## Ajouter un quiz

1. Créer le fichier des questions, par exemple `quiz/maths/suites.json` :

```json
{
  "titre": "Suites numériques",
  "niveau": "Terminale, spécialité maths",
  "questions": [
    {
      "categorie": "Suites géométriques",
      "question": "Texte de la question",
      "reponses": ["La bonne réponse", "Une mauvaise", "Une autre", "Encore une autre"],
      "explication": "Pourquoi la bonne réponse est juste.",
      "indice": "Un coup de pouce, facultatif."
    }
  ]
}
```

2. Déclarer le quiz dans `quiz/catalogue.json`, dans la liste `themes` de sa matière :

```json
{
  "id": "suites",
  "titre": "Suites numériques",
  "niveau": "Terminale spécialité",
  "description": "Une phrase qui résume le contenu.",
  "questions": 20,
  "fichier": "quiz/maths/suites.json"
}
```

Règles à respecter :

- **La première réponse de `reponses` est toujours la bonne.** Les réponses sont mélangées à l'affichage.
- `id` ne contient que des minuscules, des chiffres et des tirets : il sert d'adresse.
- `categorie` et `indice` sont facultatifs. Avec au moins deux catégories, le résultat final détaille le score par catégorie.
- Les textes des questions, réponses, indices et explications acceptent du HTML simple, par exemple `H<sub>2</sub>O` ou `10<sup>−3</sup>`.

Pour ajouter une matière, ajouter une entrée dans `matieres` avec un `id`, un `titre` et une liste `themes`.

## Tester sur son ordinateur

Le site charge ses fichiers JSON par le réseau : ouvrir `index.html` d'un double-clic ne suffit pas. Lancer un petit serveur depuis le dossier du projet :

```
python3 -m http.server 8000
```

puis ouvrir <http://localhost:8000>.

## Meilleur score

Le meilleur score de chaque quiz est gardé dans le navigateur de la personne qui joue (stockage local). Rien n'est envoyé ni partagé.
