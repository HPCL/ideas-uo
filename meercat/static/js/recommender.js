//var hostname = "https://meercat.cs.uoregon.edu:8099";
var hostname = "https://meercat.cs.uoregon.edu/dashboard/recommender/";


function generateIndividualPersonRowsHTML(personName) {
 // Do some initial data clensing
 [namesArray, emailsArray, strength] = personName;

 namesArray = namesArray.filter(function (el) {
   return el != null && el.trim() != "";
 });

 emailsArray = emailsArray.filter(function (el) {
   return el != null && el.trim() != "";
 });

 // Add HTML to rows
 tableRow = `
 <div class="row border-top p-1">
                 <div class="col">`;

 // Add name information
 $.each(namesArray, function (personNameIndex, personIndividualName) {
   if (personNameIndex == 0) {
     tableRow += `<strong>${personIndividualName}</strong>`;
   }
   else {
     tableRow += `, ${personIndividualName}`;
   }
 });

 // Add email information
 tableRow += `
                 </div>
                 <div class="col">`;

 $.each(emailsArray, function (personNameIndex, personIndividualEmail) {
   if (personNameIndex == 0) {
     tableRow += `<strong><a href="mailto:${personIndividualEmail}">${personIndividualEmail}</a></strong>`;
   }
   else {
     tableRow += `, <a href="mailto:${personIndividualEmail}">${personIndividualEmail}</a>`;
   }
 });

 // Add strength information
 percentStrength = 0;
 color = "";

 if(strength == "Strong"){
   percentStrength = "100";
   color = "bg-success";
 } else if (strength == "Medium"){
   percentStrength = "66";
   color = "bg-warning";
 } else if (strength == "Weak"){
   percentStrength = "33";
   color = "bg-danger";
 }

 tableRow += `</div>
                 <div class="col">
                     <div class="progress">
                         <div class="progress-bar ${color}" role="progressbar"
                             style="width: ${percentStrength}%" aria-valuenow="${percentStrength}" aria-valuemin="0"
                             aria-valuemax="100">${strength}</div>
                     </div>
                 </div>
             </div>`;

return tableRow;
}

function updateAllRecommendedPeople(nameData){
  if(nameData && nameData.length >0){
    $.each(nameData, function (personNameIndex, personName) {
      $("#all-recommended-people").append(generateIndividualPersonRowsHTML(personName))
    }
  )};
}

function addToFileRecommendationsAccordion(fileIndex, fileName, fileData) {
  // Add accordion item to #file-recommendations-accordion
  accordionItem =
    `<div class="accordion-item">
    <h2 class="accordion-header" id="panelsStayOpen-heading${fileIndex}">
        <button class="accordion-button collapsed" type="button" data-bs-toggle="collapse"
            data-bs-target="#panelsStayOpen-collapse${fileIndex}" aria-expanded="false"
            aria-controls="panelsStayOpen-collapse${fileIndex}">
            ${fileName}
        </button>
    </h2>
    <div id="panelsStayOpen-collapse${fileIndex}" class="accordion-collapse collapse"
        aria-labelledby="panelsStayOpen-heading${fileIndex}">
        <div class="accordion-body">

            <div>

                <div class="row p-1 text-decoration-underline">
                    <div class="col">
                        <strong><em>Person</em></strong>
                    </div>
                    <div class="col">
                        <strong><em>Email</em></strong>
                    </div>
                    <div class="col">
                        <strong><em>Strength of recommendation</em></strong>
                    </div>
                </div>`;

  // Add individual rows
  $.each(fileData, function (personIndex, personName) {

    accordionItem += generateIndividualPersonRowsHTML(personName);
    
  });

  accordionItem += `</div>
  </div>
</div>
</div>`;

  $("#file-recommendations-accordion").append(accordionItem);
};

/*
function getFileData(fileIndex, fileName) {
  return $.getJSON(hostname + "/p" + fileName, function (fileData) {
    if (fileData && fileData.length > 0) {
      addToFileRecommendationsAccordion(fileIndex, fileName, fileData);
    }
  });
};
*/

function populateView(fileNames) {
  // Set up an empty array full of JSON promises
  ajaxJSONPromises = [];

  // Iterate over each file and get associated JSON from server
  $.each(fileNames, function (index, fileName) {
    //ajaxJSONPromises.push([index, fileName], $.getJSON(hostname + "/p" + fileName));
    console.log("RECOMMENDER PUSHING "+fileName);
    ajaxJSONPromises.push([index, fileName], $.getJSON(hostname + "?project="+project+"&filename="+fileName));
  });

  // Once all the JSON calls have finished, 
  // use the data to fill the individual accordion and top-level recommenations

  $.when.apply($, ajaxJSONPromises).done(function(){
    // This callback will be called with multiple arguments, one for each AJAX call

    var allNameData = [];
    for(var i = 0, len = arguments.length; i < len; i+=2){
      [fileIndex, fileName] = ajaxJSONPromises[i];
      fileData = ajaxJSONPromises[i+1].responseJSON;
      console.log("RECOMMENDER RESULTS "+fileName);
      console.log(fileData);
      addToFileRecommendationsAccordion(fileIndex, fileName, fileData);
      allNameData.push(fileData);
    }
    // Consolidate names

    uniqueValues = {};

    for(const fileData of allNameData){
      for(const personInfo of fileData){
        // Unpack info
        [namesArray, emailsArray, strength] = personInfo;

        // Light cleaning
        namesArray = namesArray.filter(function (el) {
          return el != null && el.trim() != "";
        });

        emailsArray = emailsArray.filter(function (el) {
          return el != null && el.trim() != "";
        });

        // Assign numerical value to strength
        strengthValue = 0;
        if(strength == "Strong"){
         strengthValue = 100;
        } else if (strength == "Medium"){
          strengthValue = 66;
        } else if (strength == "Weak"){
          strengthValue = 33;
        }

        // Aggregate strength
        keyVal = JSON.stringify([namesArray, emailsArray])
        if(keyVal in uniqueValues){
          uniqueValues[keyVal] += strengthValue;
        }
        else{
          uniqueValues[keyVal] = strengthValue;
        }
      }
    }

    // Take an average of each value
    for (const [key, value] of Object.entries(uniqueValues)) {
      uniqueValues[key] = value / allNameData.length;
    }
    
    // Get the top N people{
    // Create items array
    var items = Object.keys(uniqueValues).map(function(key) {
      return [key, uniqueValues[key]];
    });

    // Sort the array based on the second element
    items.sort(function(first, second) {
      return second[1] - first[1];
    });

    // Create a new array with only the first N items
    topNames = items.slice(0, 5);
    //}

    // Convert scores back to strength numbers and key back to email and names

    consolidatedNames = []

    for (const [key, strength] of topNames) {
      [namesArray, emailsArray] = JSON.parse(key)
      strengthValue = "";
        if(strength <= 33){
         strengthValue = "Weak";
        } else if (strength <= 66){
          strengthValue = "Medium";
        } else if (strength <= 100){
          strengthValue = "Strong";
        }
      consolidatedNames.push([namesArray, emailsArray, strengthValue]);
    }

    // Display consolidation
    updateAllRecommendedPeople(consolidatedNames);
});
  
  
};