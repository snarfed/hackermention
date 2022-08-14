/**
 * Firebase Cloud Functions.
 *
 * https://firebase.google.com/docs/functions
 * https://firebase.google.com/docs/functions/database-events
 * https://firebase.google.com/docs/reference/
 */

// const firebase = require('firebase')
const functions = require('firebase-functions')
const admin = require('firebase-admin')
admin.initializeApp()

/**
 * Triggered by Firebase Realtime Database when a Hacker News item is updated.
 *
 * https://github.com/HackerNews/API
 * https://firebase.google.com/docs/functions/beta/database-events
 */
exports.itemUpdated = functions.database.instance('hacker-news').ref('/v0/item/{id}')
    .onCreate((snapshot, context) => {
      functions.logger.log('Item: ', context.params.id, snapshot.val())
      return null
})

/**
 * Serves Hacker News items as HTML with microformats2.
 */
exports.serveItem = functions.https.onRequest((request, response) => {
  functions.logger.info("Hello logs!", {structuredData: true})
  response.send("Hello from Firebase!")
})

